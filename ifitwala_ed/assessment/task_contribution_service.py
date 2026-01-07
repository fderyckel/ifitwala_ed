# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/task_contribution_service.py

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.assessment.task_submission_service import ensure_evidence_stub_submission


def mark_contributions_stale(outcome_id, latest_submission_id=None):
	if not outcome_id:
		return 0

	clauses = ["task_outcome = %(outcome)s", "is_stale = 0"]
	params = {"outcome": outcome_id}
	if latest_submission_id:
		clauses.append("task_submission != %(submission)s")
		params["submission"] = latest_submission_id

	query = f"""
		UPDATE `tabTask Contribution`
		SET is_stale = 1, modified = NOW(), modified_by = %(user)s
		WHERE {' AND '.join(clauses)}
	"""
	params["user"] = frappe.session.user or "Administrator"
	frappe.db.sql(query, params)
	return frappe.db.rowcount


def get_latest_submission_version(outcome_id):
	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))

	version = frappe.db.get_value(
		"Task Submission",
		{"task_outcome": outcome_id},
		"max(version)",
	)
	try:
		return int(version or 0)
	except Exception:
		return 0


def get_submission_version(submission_id):
	if not submission_id:
		return 0
	version = frappe.db.get_value("Task Submission", submission_id, "version")
	try:
		return int(version or 0)
	except Exception:
		return 0


def save_draft_contribution(payload, contributor=None):
	data = _normalize_payload(payload)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	submission_id = _get_payload_value(data, "task_submission", "submission")

	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))
	if not submission_id:
		submission_id = ensure_evidence_stub_submission(
			outcome_id,
			origin="Teacher Observation",
			note=data.get("evidence_note"),
		)
		data["task_submission"] = submission_id

	contributor = contributor or frappe.session.user
	contribution_type = (data.get("contribution_type") or "Self").strip()
	if not contribution_type:
		contribution_type = "Self"

	doc = _get_existing_draft(data, outcome_id, contributor, contribution_type)
	is_new = doc is None
	if is_new:
		doc = frappe.new_doc("Task Contribution")

	doc.task_outcome = outcome_id
	doc.task_submission = submission_id
	doc.contributor = contributor
	doc.contribution_type = contribution_type
	doc.status = "Draft"

	_apply_payload_fields(doc, data)

	if is_new:
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)

	return {
		"contribution": doc.name,
		"status": doc.status,
		"task_outcome": doc.task_outcome,
		"task_submission": doc.task_submission,
	}


def submit_contribution(payload, contributor=None):
	data = _normalize_payload(payload)
	contributor = contributor or frappe.session.user

	name = data.get("name") or data.get("draft_name")
	if name:
		doc = frappe.get_doc("Task Contribution", name)
		if doc.contributor and doc.contributor != contributor:
			frappe.throw(_("Draft contribution belongs to another contributor."))
		if doc.status != "Draft":
			frappe.throw(_("Only draft contributions can be submitted."))
		doc.status = "Submitted"
		doc.contributor = contributor
		if data.get("task_submission"):
			doc.task_submission = data.get("task_submission")
		if data.get("task_outcome"):
			doc.task_outcome = data.get("task_outcome")
		if not doc.task_submission:
			doc.task_submission = ensure_evidence_stub_submission(
				doc.task_outcome,
				origin="Teacher Observation",
				note=data.get("evidence_note"),
			)
			data["task_submission"] = doc.task_submission
		if not doc.task_submission:
			frappe.throw(_("Task Submission is required."))
		doc.submitted_on = now_datetime()
		_apply_payload_fields(doc, data)
		doc.save(ignore_permissions=True)
		from ifitwala_ed.assessment.task_outcome_service import apply_official_outcome_from_contributions

		outcome_update = apply_official_outcome_from_contributions(doc.task_outcome)
		return {
			"contribution": doc.name,
			"status": doc.status,
			"task_outcome": doc.task_outcome,
			"task_submission": doc.task_submission,
			"outcome_update": outcome_update,
		}

	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	submission_id = _get_payload_value(data, "task_submission", "submission")
	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))
	if not submission_id:
		submission_id = ensure_evidence_stub_submission(
			outcome_id,
			origin="Teacher Observation",
			note=data.get("evidence_note"),
		)
		data["task_submission"] = submission_id

	contribution_type = (data.get("contribution_type") or "Self").strip()
	if not contribution_type:
		contribution_type = "Self"

	doc = frappe.new_doc("Task Contribution")
	doc.task_outcome = outcome_id
	doc.task_submission = submission_id
	doc.contributor = contributor
	doc.contribution_type = contribution_type
	doc.status = "Submitted"
	doc.submitted_on = now_datetime()
	_apply_payload_fields(doc, data)
	doc.insert(ignore_permissions=True)

	from ifitwala_ed.assessment.task_outcome_service import apply_official_outcome_from_contributions

	outcome_update = apply_official_outcome_from_contributions(doc.task_outcome)
	return {
		"contribution": doc.name,
		"status": doc.status,
		"task_outcome": doc.task_outcome,
		"task_submission": doc.task_submission,
		"outcome_update": outcome_update,
	}


def apply_moderator_action(payload, contributor=None):
	data = _normalize_payload(payload)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	submission_id = _get_payload_value(data, "task_submission", "submission")
	action = (data.get("action") or data.get("moderation_action") or "").strip()

	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))
	if not submission_id:
		submission_id = ensure_evidence_stub_submission(
			outcome_id,
			origin="Teacher Observation",
			note=data.get("evidence_note"),
		)
		data["task_submission"] = submission_id
	if not action:
		frappe.throw(_("Moderation action is required."))

	contributor = contributor or frappe.session.user

	doc = frappe.new_doc("Task Contribution")
	doc.task_outcome = outcome_id
	doc.task_submission = submission_id
	doc.contributor = contributor
	doc.contribution_type = "Moderator"
	doc.moderation_action = action
	doc.status = "Submitted"
	doc.submitted_on = now_datetime()
	_apply_payload_fields(doc, data)
	doc.insert(ignore_permissions=True)

	from ifitwala_ed.assessment.task_outcome_service import apply_official_outcome_from_contributions

	outcome_update = apply_official_outcome_from_contributions(doc.task_outcome)
	return {
		"contribution": doc.name,
		"status": doc.status,
		"task_outcome": doc.task_outcome,
		"task_submission": doc.task_submission,
		"outcome_update": outcome_update,
	}


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


def _get_existing_draft(data, outcome_id, contributor, contribution_type):
	if data.get("name") or data.get("draft_name"):
		name = data.get("name") or data.get("draft_name")
		doc = frappe.get_doc("Task Contribution", name)
		if doc.contributor and doc.contributor != contributor:
			frappe.throw(_("Draft contribution belongs to another contributor."))
		if doc.status != "Draft":
			frappe.throw(_("Only draft contributions can be edited."))
		return doc

	name = frappe.db.get_value(
		"Task Contribution",
		{
			"task_outcome": outcome_id,
			"contributor": contributor,
			"contribution_type": contribution_type,
			"status": "Draft",
		},
		"name",
	)
	if name:
		return frappe.get_doc("Task Contribution", name)
	return None


def _apply_payload_fields(doc, data):
	for fieldname in ("score", "grade", "feedback", "moderation_action"):
		if fieldname in data:
			setattr(doc, fieldname, data.get(fieldname))

	if "rubric_scores" in data:
		doc.set("rubric_scores", data.get("rubric_scores") or [])
