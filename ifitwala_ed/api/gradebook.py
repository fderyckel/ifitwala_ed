# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/gradebook.py

# Gradebook API controller (UI-facing).
# - Grid reads Task Outcome only
# - Drawer shows Outcome + Submissions + Contributions
# - Contribution actions call service layer (no grade computation here)

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.assessment import task_contribution_service


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
	"""
	One batched lookup for student labels, to avoid N+1 in grid.
	Adjust fields if your Student doctype differs.
	"""
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
			"name",
			"task",
			"student_group",
			"delivery_mode",
			"grading_mode",
			"grade_scale",
			"max_points",
			"course",
			"academic_year",
			"school",
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
		student_map = _get_student_display_map([row.get("student") for row in outcomes])

	for row in outcomes:
		row["student_label"] = student_map.get(row.get("student")) if student_map else None

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

	outcome_fields = [
		"name",
		"task_delivery",
		"task",
		"student",
		"student_group",
		"submission_status",
		"grading_status",
		"procedural_status",
		"has_submission",
		"has_new_submission",
		"is_stale",
		"is_complete",
		"completed_on",
		"official_score",
		"official_grade",
		"official_grade_value",
		"grade_scale",
		"official_feedback",
	]

	outcome_row = frappe.db.get_value("Task Outcome", outcome, outcome_fields, as_dict=True)
	if not outcome_row:
		frappe.throw(_("Task Outcome not found."))

	submissions = frappe.get_all(
		"Task Submission",
		filters={"task_outcome": outcome_row["name"]},
		fields=[
			"name",
			"version",
			"submitted_on",
			"submitted_by",
			"is_late",
			"is_cloned",
			"cloned_from",
			"link_url",
			"text_content",
		],
		order_by="version desc",
		limit_page_length=50,
	)

	contributions = frappe.get_all(
		"Task Contribution",
		filters={"task_outcome": outcome_row["name"]},
		fields=[
			"name",
			"task_submission",
			"contributor",
			"contribution_type",
			"status",
			"submitted_on",
			"score",
			"grade",
			"grade_value",
			"feedback",
			"is_stale",
			"moderation_action",
		],
		order_by="submitted_on desc",
		limit_page_length=100,
	)

	return {
		"outcome": outcome_row,
		"submissions": submissions,
		"contributions": contributions,
	}


@frappe.whitelist()
def save_contribution_draft(payload):
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	return task_contribution_service.save_draft_contribution(payload)


@frappe.whitelist()
def submit_contribution(payload):
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	return task_contribution_service.submit_contribution(payload)


@frappe.whitelist()
def moderator_action(payload):
	if not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	return task_contribution_service.apply_moderator_action(payload)


@frappe.whitelist()
def mark_new_submission_seen(outcome: str):
	"""
	UI convenience: when teacher opens drawer, they can clear the 'new evidence' flag.
	This only flips has_new_submission; it does NOT change submission_status.
	"""
	_require(outcome, "Task Outcome")
	if not _can_write_gradebook() and not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	frappe.db.set_value("Task Outcome", outcome, "has_new_submission", 0, update_modified=True)
	return {"ok": True, "outcome": outcome, "has_new_submission": 0}
