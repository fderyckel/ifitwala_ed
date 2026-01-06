# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/task.py

# Task Planning API controller (UI-facing).
# - Task library search
# - Task detail payload for delivery wizard
# - Task Delivery creation via service

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.assessment.task_delivery_service import create_delivery


def _require(value, label):
	if not value:
		frappe.throw(_("{0} is required.").format(label))


def _has_role(*roles):
	user_roles = set(frappe.get_roles(frappe.session.user))
	return any(role in user_roles for role in roles)


def _can_plan_tasks():
	return _has_role("System Manager", "Academic Admin", "Curriculum Coordinator", "Instructor")


def _normalize_payload(payload):
	if payload is None:
		return {}
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("Payload must be a dict."))
	return payload


@frappe.whitelist()
def search_tasks(filters=None, query=None, limit=20, start=0):
	if not _can_plan_tasks():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	filters = _normalize_payload(filters)
	if query:
		filters["title"] = ["like", f"%{query.strip()}%"]

	try:
		limit = int(limit or 20)
		start = int(start or 0)
	except Exception:
		limit = 20
		start = 0

	fields = [
		"name",
		"title",
		"task_type",
		"default_course",
		"is_template",
		"is_archived",
	]

	return frappe.get_all(
		"Task",
		filters=filters,
		fields=fields,
		order_by="is_template desc, modified desc",
		limit_page_length=limit,
		limit_start=start,
	)


@frappe.whitelist()
def get_task_for_delivery(task):
	_require(task, "Task")
	if not _can_plan_tasks():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	fields = [
		"name",
		"title",
		"task_type",
		"default_course",
		"learning_unit",
		"lesson",
		"instructions",
		"is_template",
		"is_archived",
		"default_delivery_mode",
		"default_requires_submission",
		"default_grading_mode",
		"default_max_points",
		"default_grade_scale",
		"default_rubric",
		"prevent_late_submission",
	]

	row = frappe.db.get_value("Task", task, fields, as_dict=True)
	if not row:
		frappe.throw(_("Task not found."))

	attachments = frappe.get_all(
		"Attached Document",
		filters={"parent": task, "parenttype": "Task"},
		fields=[
			"name",
			"file",
			"file_name",
			"file_size",
			"external_url",
			"description",
			"is_primary",
		],
		order_by="idx asc",
	)

	return {
		"task": row,
		"attachments": attachments,
	}


@frappe.whitelist()
def create_task_delivery(payload):
	if not _can_plan_tasks():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	data = _normalize_payload(payload)
	_require(data.get("task"), "Task")
	_require(data.get("student_group"), "Student Group")

	return create_delivery(data)
