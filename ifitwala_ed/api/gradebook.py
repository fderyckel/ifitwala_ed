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
from ifitwala_ed.assessment import task_outcome_service


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
			"link_url", "text_content", "attachments"
		],
		order_by="version desc",
		limit_page_length=20,
	)

	return {
		"outcome": outcome_doc,
		"submissions": submissions,
		"contributions": [], # contributions fetched lazily or empty for now
	}


@frappe.whitelist()
def save_outcome_draft(outcome: str, official_score=None, official_grade=None, official_feedback=None, procedural_status=None):
	"""
	Save grading draft.
	"""
	_require(outcome, "Task Outcome")
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	return task_outcome_service.update_manual_outcome_draft(
		outcome_id=outcome,
		official_score=official_score,
		official_grade=official_grade,
		official_feedback=official_feedback,
		procedural_status=procedural_status
	)


@frappe.whitelist()
def submit_outcome_contribution(outcome: str):
	"""
	Submit contribution (moves to Needs Review).
	"""
	_require(outcome, "Task Outcome")
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	return task_outcome_service.submit_contribution_placeholder(outcome)


@frappe.whitelist()
def moderator_action(outcome: str, action: str, note: str | None = None):
	"""
	Moderator action (Approve/Return/etc).
	"""
	_require(outcome, "Task Outcome")
	_require(action, "Action")
	if not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	return task_outcome_service.process_moderator_action(outcome, action, note)


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
