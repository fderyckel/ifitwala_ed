# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/gradebook.py

# Gradebook API Controller (Teacher Grading Loop)
# - Get Gradebook Grid (read-only optimization)
# - Get Grading Drawer (Outcome + Submissions + History)
# - Actions: Save Draft, Submit, Moderate (via Services)
#
# REGRESSION TRAP:
# Controllers must not write official_* fields to Task Outcome.
# Use task_outcome_service or task_contribution_service for all writes.

from __future__ import annotations

import frappe
from frappe import _
from ifitwala_ed.assessment import task_contribution_service
from ifitwala_ed.assessment import task_outcome_service
from ifitwala_ed.assessment import task_submission_service


# ---------------------------
# Public endpoints (UI)
# ---------------------------

@frappe.whitelist()
def get_grid(task_delivery: str, include_students: int = 1):
	"""
	Grid = Task Outcome rows for a single Task Delivery.
	"""
	_require(task_delivery, "Task Delivery")

	if not _can_write_gradebook() and not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	delivery = frappe.db.get_value(
		"Task Delivery",
		task_delivery,
		[
			"name", "task", "student_group",
			"delivery_mode", "grading_mode",
			"grade_scale", "max_points",
			"course", "academic_year", "school",
		],
		as_dict=True,
	)
	if not delivery:
		frappe.throw(_("Task Delivery not found."))

	outcome_fields = [
		"name as outcome",
		"student",
		"submission_status",
		"grading_status",
		"procedural_status",
		"has_submission",
		"has_new_submission",
		"is_stale",
		"is_complete",
		"official_score",
		"official_grade",
		"official_grade_value",
	]

	outcomes = frappe.get_all(
		"Task Outcome",
		filters={"task_delivery": task_delivery},
		fields=outcome_fields,
		order_by="student asc",
		limit_page_length=0,
	)

	student_map = {}
	if int(include_students) == 1:
		student_map = _get_student_display_map([r.get("student") for r in outcomes])

	for r in outcomes:
		r["student_label"] = student_map.get(r.get("student")) if student_map else None

	return {
		"task_delivery": delivery["name"],
		"task": delivery.get("task"),
		"student_group": delivery.get("student_group"),
		"delivery_mode": delivery.get("delivery_mode"),
		"grading_mode": delivery.get("grading_mode"),
		"grade_scale": delivery.get("grade_scale"),
		"max_points": delivery.get("max_points"),
		"course": delivery.get("course"),
		"academic_year": delivery.get("academic_year"),
		"school": delivery.get("school"),
		"rows": outcomes,
	}


@frappe.whitelist()
def get_drawer(outcome: str):
	"""
	Drawer payload for a single outcome.
	"""
	_require(outcome, "Task Outcome")

	if not _can_write_gradebook() and not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	# Fetch Outcome
	outcome_fields = [
		"name", "task_delivery", "task", "student", "student_group",
		"submission_status", "grading_status", "procedural_status",
		"has_submission", "has_new_submission", "is_stale",
		"is_complete", "completed_on",
		"official_score", "official_grade", "official_grade_value",
		"grade_scale", "official_feedback",
	]
	outcome_doc = frappe.db.get_value("Task Outcome", outcome, outcome_fields, as_dict=True)
	if not outcome_doc:
		frappe.throw(_("Task Outcome not found."))

	# Fetch Submissions
	submissions = frappe.get_all(
		"Task Submission",
		filters={"task_outcome": outcome},
		fields=[
			"name", "version", "submitted_on", "submitted_by",
			"is_late", "is_cloned", "cloned_from",
			"submission_origin", "is_stub", "evidence_note",
			"link_url", "text_content", "attachments"
		],
		order_by="version desc",
		limit_page_length=20,
	)

	contributions = frappe.get_all(
		"Task Contribution",
		filters={"task_outcome": outcome},
		fields=[
			"name",
			"contributor",
			"contribution_type",
			"status",
			"is_stale",
			"task_submission",
			"score",
			"grade",
			"grade_value",
			"feedback",
			"moderation_action",
			"submitted_on",
			"modified",
		],
		order_by="submitted_on desc, modified desc",
		limit_page_length=100,
	)

	current_user = frappe.session.user
	my_draft = None
	my_latest_submitted = None
	for row in contributions:
		if row.get("contributor") != current_user:
			continue
		if row.get("status") == "Draft" and not my_draft:
			my_draft = row
		if row.get("status") == "Submitted" and not my_latest_submitted:
			my_latest_submitted = row
		if my_draft and my_latest_submitted:
			break

	return {
		"outcome": outcome_doc,
		"latest_submission": submissions[0] if submissions else None,
		"submissions": submissions,
		"contributions": contributions,
		"my_draft": my_draft,
		"my_latest_submitted": my_latest_submitted,
		"compare_contributions": [],
	}


@frappe.whitelist()
def save_draft(payload=None, **kwargs):
	"""
	Save a draft contribution (no direct Outcome writes).
	"""
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	data = payload or kwargs
	if not data:
		frappe.throw(_("Contribution payload is required."))
	_reject_official_fields(data)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	_require(outcome_id, "Task Outcome")
	data["task_submission"] = _resolve_submission_id(outcome_id, data)
	result = task_contribution_service.save_draft_contribution(data, contributor=frappe.session.user)
	return {
		"result": result,
		"outcome": _get_outcome_summary(outcome_id),
	}


@frappe.whitelist()
def submit_contribution(payload=None, **kwargs):
	"""
	Submit a contribution (no direct Outcome writes).
	"""
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	data = payload or kwargs
	if not data:
		frappe.throw(_("Contribution payload is required."))
	_reject_official_fields(data)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	_require(outcome_id, "Task Outcome")
	data["task_submission"] = _resolve_submission_id(outcome_id, data)
	result = task_contribution_service.submit_contribution(data, contributor=frappe.session.user)
	return {
		"result": result,
		"outcome": _get_outcome_summary(outcome_id),
	}


@frappe.whitelist()
def save_contribution_draft(payload=None, **kwargs):
	return save_draft(payload=payload, **kwargs)


@frappe.whitelist()
def moderator_action(payload=None, **kwargs):
	"""
	Moderator action (Approve/Return/etc) via contributions.
	"""
	if not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	data = payload or kwargs
	if not data:
		frappe.throw(_("Moderation payload is required."))
	_reject_official_fields(data)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	_require(outcome_id, "Task Outcome")
	data["task_submission"] = _resolve_submission_id(outcome_id, data)
	result = task_contribution_service.apply_moderator_action(data, contributor=frappe.session.user)
	return {
		"result": result,
		"outcome": _get_outcome_summary(outcome_id),
	}


@frappe.whitelist()
def mark_new_submission_seen(outcome: str):
	"""
	Clear 'New Evidence' flag.
	"""
	_require(outcome, "Task Outcome")
	if not _can_write_gradebook() and not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	return task_outcome_service.mark_new_submission_seen(outcome)


# ---------------------------
# Helpers
# ---------------------------

def _require(value, label):
	if not value:
		frappe.throw(_("{0} is required.").format(label))


def _has_role(*roles):
	user_roles = set(frappe.get_roles(frappe.session.user))
	return any(role in user_roles for role in roles)


def _is_academic_adminish():
	return _has_role("System Manager", "Academic Admin", "Admin Assistant", "Curriculum Coordinator")


def _can_write_gradebook():
	return _has_role("System Manager", "Academic Admin", "Curriculum Coordinator", "Instructor")


def _get_student_display_map(student_ids):
	if not student_ids:
		return {}

	meta = frappe.get_meta("Student")
	fields = ["name"]
	if meta.get_field("student_name"):
		fields.append("student_name")
	elif meta.get_field("full_name"):
		fields.append("full_name")
	else:
		if meta.get_field("first_name"):
			fields.append("first_name")
		if meta.get_field("last_name"):
			fields.append("last_name")

	rows = frappe.get_all(
		"Student",
		filters={"name": ["in", list(set(student_ids))]},
		fields=fields,
		limit_page_length=0,
	)

	out = {}
	for row in rows:
		label = row.get("student_name") or row.get("full_name")
		if not label:
			fn = (row.get("first_name") or "").strip()
			ln = (row.get("last_name") or "").strip()
			label = (fn + " " + ln).strip() or row["name"]
		out[row["name"]] = label

	return out


def _get_outcome_summary(outcome_id):
	if not outcome_id:
		return None

	fields = [
		"name",
		"grading_status",
		"submission_status",
		"procedural_status",
		"has_submission",
		"has_new_submission",
		"is_stale",
		"is_complete",
		"official_score",
		"official_grade",
		"official_grade_value",
		"official_feedback",
	]
	return frappe.db.get_value("Task Outcome", outcome_id, fields, as_dict=True)


def _reject_official_fields(payload):
	if not isinstance(payload, dict):
		return
	for key in payload.keys():
		if key.startswith("official_"):
			frappe.throw(_("official_* fields are not accepted in gradebook endpoints."))


def _get_payload_value(data, *keys):
	for key in keys:
		if key in data and data.get(key) not in (None, ""):
			return data.get(key)
	return None


def _resolve_submission_id(outcome_id, payload):
	submission_id = _get_payload_value(payload, "task_submission", "submission")
	if submission_id:
		return submission_id

	latest = frappe.get_all(
		"Task Submission",
		filters={"task_outcome": outcome_id},
		fields=["name", "version", "is_stub"],
		order_by="version desc",
		limit_page_length=1,
	)
	if latest:
		return latest[0]["name"]

	return task_submission_service.create_evidence_stub(
		outcome_id,
		created_by=frappe.session.user,
		note=payload.get("evidence_note"),
	)
