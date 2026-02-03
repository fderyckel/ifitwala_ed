# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/task_submission_service.py

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.assessment.task_contribution_service import mark_contributions_stale


def get_next_submission_version(outcome_id):
	if not outcome_id:
		frappe.throw(_("Task Outcome is required for submissions."))

	max_version = frappe.db.get_value(
		"Task Submission",
		{"task_outcome": outcome_id},
		"max(version)",
	)
	try:
		max_version = int(max_version or 0)
	except Exception:
		max_version = 0
	return max_version + 1


def create_student_submission(payload, user=None, uploaded_files=None):
	data = _normalize_payload(payload)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))

	outcome_row = frappe.db.get_value(
		"Task Outcome",
		outcome_id,
		[
			"student",
			"student_group",
			"course",
			"academic_year",
			"school",
			"task_delivery",
			"task",
		],
		as_dict=True,
	)
	if not outcome_row:
		frappe.throw(_("Task Outcome not found."))

	text_content = (data.get("text_content") or "").strip()
	link_url = (data.get("link_url") or "").strip()
	attachments = data.get("attachments") or []
	if attachments:
		frappe.throw(_("Attachments must be uploaded as raw files via dispatcher."))

	uploaded_files = uploaded_files or []
	has_uploads = bool(uploaded_files)

	if not text_content and not link_url and not has_uploads:
		frappe.throw(_("Student evidence is required."))

	next_version = get_next_submission_version(outcome_id)

	doc = frappe.new_doc("Task Submission")
	doc.task_outcome = outcome_id
	doc.version = next_version
	doc.submitted_by = user or frappe.session.user
	doc.submitted_on = now_datetime()
	doc.submission_origin = "Student Upload"
	doc.is_stub = 0
	doc.text_content = text_content or None
	doc.link_url = link_url or None
	if data.get("evidence_note"):
		doc.evidence_note = data.get("evidence_note")
	if has_uploads:
		doc.set_new_name()
		_attach_submission_files(doc, outcome_row, uploaded_files, data.get("upload_source"))

	stamp_submission_context(doc, outcome_row)
	doc.insert(ignore_permissions=True)

	submission_status = "Submitted" if next_version == 1 else "Resubmitted"
	frappe.db.set_value(
		"Task Outcome",
		outcome_id,
		{
			"has_submission": 1,
			"has_new_submission": 1,
			"submission_status": submission_status,
		},
		update_modified=True,
	)

	mark_contributions_stale(outcome_id, latest_submission_id=doc.name)

	return {
		"submission_id": doc.name,
		"version": next_version,
		"outcome_flags": {
			"has_submission": True,
			"has_new_submission": True,
			"submission_status": submission_status,
		},
	}


def _attach_submission_files(submission_doc, outcome_row, uploaded_files, upload_source=None):
	from ifitwala_ed.utilities import file_dispatcher, file_management

	student = outcome_row.get("student")
	school = outcome_row.get("school")
	task_name = outcome_row.get("task") or submission_doc.name

	if not student:
		frappe.throw(_("Student is required for file classification."))
	if not school:
		frappe.throw(_("School is required for file classification."))

	organization = frappe.db.get_value("School", school, "organization")
	if not organization:
		frappe.throw(_("Organization is required for file classification."))

	settings = file_management.get_settings()
	context_override = file_management.build_task_submission_context(
		student=student,
		task_name=task_name,
		settings=settings,
	)

	source = upload_source or "API"
	for upload in uploaded_files:
		file_name = upload.get("file_name") or upload.get("filename")
		content = upload.get("content")
		if not file_name or not content:
			frappe.throw(_("Uploaded files must include file_name and content."))

		file_doc = file_dispatcher.create_and_classify_file(
			file_kwargs={
				"attached_to_doctype": "Task Submission",
				"attached_to_name": submission_doc.name,
				"is_private": 1,
				"file_name": file_name,
				"content": content,
			},
			classification={
				"primary_subject_type": "Student",
				"primary_subject_id": student,
				"data_class": "academic",
				"purpose": "assessment_submission",
				"retention_policy": "until_program_end_plus_1y",
				"slot": "submission",
				"organization": organization,
				"school": school,
				"upload_source": source,
			},
			context_override=context_override,
		)

		submission_doc.append("attachments", {
			"file": file_doc.file_url,
			"file_name": file_doc.file_name,
			"file_size": file_doc.file_size,
			"public": 0,
		})


def stamp_submission_context(submission_doc, outcome_row):
	if not outcome_row:
		return

	fieldnames = [
		"student",
		"student_group",
		"course",
		"academic_year",
		"school",
		"task_delivery",
		"task",
	]
	for field in fieldnames:
		if outcome_row.get(field) and hasattr(submission_doc, field):
			if not getattr(submission_doc, field, None):
				setattr(submission_doc, field, outcome_row.get(field))


def apply_outcome_submission_effects(outcome_id, submission_id, source="student"):
	if not outcome_id or not submission_id:
		return

	outcome = frappe.db.get_value(
		"Task Outcome",
		outcome_id,
		[
			"grading_status",
			"official_score",
			"official_grade",
			"official_feedback",
			"has_new_submission",
			"has_submission",
			"is_stale",
		],
		as_dict=True,
	) or {}

	if source == "teacher_stub":
		updates = {"submission_status": "Submitted"}
		if "has_submission" in outcome:
			updates["has_submission"] = 1
		if "has_new_submission" in outcome:
			updates["has_new_submission"] = 0
		if "is_stale" in outcome:
			updates["is_stale"] = 0
		frappe.db.set_value("Task Outcome", outcome_id, updates, update_modified=True)
		return

	submission = frappe.db.get_value(
		"Task Submission",
		submission_id,
		["is_late"],
		as_dict=True,
	) or {}

	grading_started = _grading_started(outcome)
	updates = {"submission_status": "Late" if submission.get("is_late") else "Submitted"}

	if "has_submission" in outcome:
		updates["has_submission"] = 1

	if "has_new_submission" in outcome:
		updates["has_new_submission"] = 1

	if "is_stale" in outcome:
		updates["is_stale"] = 1 if grading_started else 0

	frappe.db.set_value("Task Outcome", outcome_id, updates, update_modified=True)

	mark_contributions_stale(outcome_id, latest_submission_id=submission_id)


def clone_group_submission(original_submission_id, outcome_ids):
	if not original_submission_id or not outcome_ids:
		return 0

	outcome_ids = [outcome_id for outcome_id in outcome_ids if outcome_id]
	if not outcome_ids:
		return 0

	original = frappe.get_doc("Task Submission", original_submission_id)
	if not original.task_outcome:
		return 0

	outcome_ids = [oid for oid in outcome_ids if oid != original.task_outcome]
	if not outcome_ids:
		return 0

	existing = frappe.db.get_values(
		"Task Submission",
		{"task_outcome": ["in", outcome_ids], "cloned_from": original_submission_id},
		"task_outcome",
		as_list=True,
	)
	existing_outcomes = {row[0] for row in existing if row and row[0]}
	target_outcomes = [oid for oid in outcome_ids if oid not in existing_outcomes]
	if not target_outcomes:
		return 0

	max_versions = _max_versions_for_outcomes(target_outcomes)
	created = 0

	for outcome_id in target_outcomes:
		version = max_versions.get(outcome_id, 0) + 1
		doc = frappe.get_doc({
			"doctype": "Task Submission",
			"task_outcome": outcome_id,
			"task_delivery": original.task_delivery,
			"task": original.task,
			"version": version,
			"submitted_by": original.submitted_by,
			"submitted_on": original.submitted_on or now_datetime(),
			"is_late": original.is_late,
			"is_cloned": 1,
			"cloned_from": original_submission_id,
			"link_url": original.link_url,
			"text_content": original.text_content,
			"attachments": _clone_attachments(original),
		})
		doc.insert(ignore_permissions=True)
		apply_outcome_submission_effects(outcome_id, doc.name, source="student")
		created += 1

	return created


def _max_versions_for_outcomes(outcome_ids):
	if not outcome_ids:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT task_outcome, MAX(version) AS max_version
		FROM `tabTask Submission`
		WHERE task_outcome IN %(outcomes)s
		GROUP BY task_outcome
		""",
		{"outcomes": tuple(outcome_ids)},
		as_dict=True,
	)
	return {row["task_outcome"]: int(row.get("max_version") or 0) for row in rows}


def _clone_attachments(original):
	attachments = []
	for row in original.get("attachments") or []:
		attachments.append({
			"section_break_sbex": row.get("section_break_sbex"),
			"file": row.get("file"),
			"external_url": row.get("external_url"),
			"description": row.get("description"),
			"public": row.get("public"),
			"version": row.get("version"),
			"effective_date": row.get("effective_date"),
			"expiry_date": row.get("expiry_date"),
			"file_name": row.get("file_name"),
			"file_size": row.get("file_size"),
			"is_primary": row.get("is_primary"),
		})
	return attachments


def ensure_evidence_stub_submission(outcome_id, origin="Teacher Observation", note=None, created_by=None):
	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))

	outcome_row = frappe.db.get_value(
		"Task Outcome",
		outcome_id,
		[
			"student",
			"student_group",
			"course",
			"academic_year",
			"school",
			"task_delivery",
			"task",
		],
		as_dict=True,
	)
	if not outcome_row:
		frappe.throw(_("Task Outcome not found."))

	latest_real = frappe.get_all(
		"Task Submission",
		filters={"task_outcome": outcome_id, "is_stub": ["!=", 1]},
		fields=["name", "version", "is_stub", "submission_origin"],
		order_by="version desc",
		limit_page_length=1,
	)
	if latest_real:
		return latest_real[0]["name"]

	latest_stub = frappe.get_all(
		"Task Submission",
		filters={"task_outcome": outcome_id, "is_stub": 1},
		fields=["name", "version", "is_stub", "submission_origin"],
		order_by="version desc",
		limit_page_length=1,
	)
	if latest_stub:
		return latest_stub[0]["name"]

	meta = frappe.get_meta("Task Submission")
	doc = frappe.new_doc("Task Submission")
	doc.task_outcome = outcome_id
	doc.version = get_next_submission_version(outcome_id)
	if meta.get_field("submitted_by"):
		doc.submitted_by = created_by or frappe.session.user
	if meta.get_field("submitted_on"):
		doc.submitted_on = now_datetime()
	if meta.get_field("submission_origin"):
		doc.submission_origin = origin
	if meta.get_field("is_stub"):
		doc.is_stub = 1
	if meta.get_field("evidence_note"):
		doc.evidence_note = note or "Evidence stub (no student submission)"
	elif meta.get_field("text_content"):
		doc.text_content = note or "Evidence stub (no student submission)"

	stamp_submission_context(doc, outcome_row)
	doc.insert(ignore_permissions=True)
	apply_outcome_submission_effects(outcome_id, doc.name, source="teacher_stub")
	return doc.name


def create_evidence_stub(outcome_id, created_by=None, note=None):
	return ensure_evidence_stub_submission(
		outcome_id,
		origin="Teacher Observation",
		note=note,
		created_by=created_by,
	)


def _normalize_payload(payload):
	if payload is None:
		return {}
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("Payload must be a dict."))
	return payload


def _get_payload_value(data, *keys):
	for key in keys:
		if key in data and data.get(key) not in (None, ""):
			return data.get(key)
	return None


def _grading_started(outcome):
	status = (outcome.get("grading_status") or "").strip()
	if status and status not in ("Not Applicable", "Not Started"):
		return True
	if outcome.get("official_score") not in (None, ""):
		return True
	if (outcome.get("official_grade") or "").strip():
		return True
	if (outcome.get("official_feedback") or "").strip():
		return True
	return False
