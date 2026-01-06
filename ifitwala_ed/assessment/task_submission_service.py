# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

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


def apply_outcome_submission_effects(outcome_id, submission_id):
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

	submission = frappe.db.get_value(
		"Task Submission",
		submission_id,
		["is_late"],
		as_dict=True,
	) or {}

	grading_started = _grading_started(outcome)
	already_new = int(outcome.get("has_new_submission") or 0) == 1
	updates = {"submission_status": "Late" if submission.get("is_late") else "Submitted"}

	if "has_submission" in outcome:
		updates["has_submission"] = 1

	if "has_new_submission" in outcome:
		updates["has_new_submission"] = 1 if (grading_started or already_new) else 0

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
		apply_outcome_submission_effects(outcome_id, doc.name)
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
