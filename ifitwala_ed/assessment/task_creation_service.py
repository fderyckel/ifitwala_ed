# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/task_creation_service.py

import frappe
from frappe import _
from frappe.utils import cint


V1_GRADING_MODES = {"None", "Completion", "Binary", "Points"}


def _parse_options(doctype, fieldname):
	meta = frappe.get_meta(doctype)
	field = meta.get_field(fieldname)
	if not field or not field.options:
		return []
	return [opt.strip() for opt in field.options.split("\n") if opt.strip()]


def _normalize_payload(payload):
	if not payload:
		frappe.throw(_("Payload is required."))
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("Payload must be a dict."))
	return payload


def _validate_payload(payload):
	allowed_keys = {
		"title",
		"instructions",
		"task_type",
		"is_template",
		"student_group",
		"delivery_mode",
		"available_from",
		"due_date",
		"lock_date",
		"allow_late_submission",
		"group_submission",
		"grading_mode",
		"max_points",
		"grade_scale",
	}
	extra = set(payload.keys()) - allowed_keys
	if extra:
		frappe.throw(_("Unsupported payload fields: {0}").format(", ".join(sorted(extra))))

	title = (payload.get("title") or "").strip()
	if not title:
		frappe.throw(_("Title is required."))

	student_group = payload.get("student_group")
	if not student_group:
		frappe.throw(_("Student group is required."))

	delivery_mode = payload.get("delivery_mode")
	if not delivery_mode:
		frappe.throw(_("Delivery mode is required."))

	task_type = payload.get("task_type")
	if task_type:
		task_type_options = set(_parse_options("Task", "task_type"))
		if task_type not in task_type_options:
			frappe.throw(_("Invalid task type: {0}").format(task_type))

	delivery_options = set(_parse_options("Task Delivery", "delivery_mode"))
	if delivery_mode not in delivery_options:
		frappe.throw(_("Invalid delivery mode: {0}").format(delivery_mode))

	grading_mode = payload.get("grading_mode")
	if grading_mode in ("", None):
		grading_mode = None

	if grading_mode is not None and grading_mode not in V1_GRADING_MODES:
		frappe.throw(_("Invalid grading mode for v1: {0}").format(grading_mode))

	if grading_mode == "Points":
		max_points = payload.get("max_points")
		if max_points in (None, ""):
			frappe.throw(_("Max points is required for points grading."))
		try:
			float(max_points)
		except (TypeError, ValueError):
			frappe.throw(_("Max points must be a valid number."))

	grade_scale = payload.get("grade_scale")
	if grade_scale and grading_mode in (None, "None"):
		frappe.throw(_("Grade scale is only allowed when grading is enabled."))

	return {
		"title": title,
		"instructions": payload.get("instructions"),
		"task_type": task_type,
		"is_template": payload.get("is_template"),
		"student_group": student_group,
		"delivery_mode": delivery_mode,
		"available_from": payload.get("available_from"),
		"due_date": payload.get("due_date"),
		"lock_date": payload.get("lock_date"),
		"allow_late_submission": payload.get("allow_late_submission"),
		"group_submission": payload.get("group_submission"),
		"grading_mode": grading_mode,
		"max_points": payload.get("max_points"),
		"grade_scale": grade_scale,
	}


@frappe.whitelist()
def create_task_and_delivery(payload):
	payload = _normalize_payload(payload)
	data = _validate_payload(payload)
	frappe.db.savepoint("create_task_and_delivery")

	task = None
	delivery = None
	try:
		task = frappe.new_doc("Task")
		task.title = data["title"]

		if data.get("instructions"):
			task.instructions = data["instructions"]
		if data.get("task_type"):
			task.task_type = data["task_type"]

		task.is_template = cint(data.get("is_template")) if data.get("is_template") is not None else 0

		course = frappe.db.get_value("Student Group", data["student_group"], "course")
		if not course:
			frappe.throw(_("Student group is missing a course."))

		task.default_course = course
		task.default_delivery_mode = data["delivery_mode"]
		task.default_grading_mode = data["grading_mode"] or "None"
		task.default_requires_submission = 1 if data["delivery_mode"] in ("Collect Work", "Assess") else 0

		if data.get("grade_scale") and data["grading_mode"] not in (None, "None"):
			task.default_grade_scale = data["grade_scale"]

		task.insert()

		delivery = frappe.new_doc("Task Delivery")
		delivery.task = task.name
		delivery.student_group = data["student_group"]
		delivery.delivery_mode = data["delivery_mode"]

		if data.get("available_from"):
			delivery.available_from = data["available_from"]
		if data.get("due_date"):
			delivery.due_date = data["due_date"]
		if data.get("lock_date"):
			delivery.lock_date = data["lock_date"]

		allow_late = data.get("allow_late_submission")
		delivery.allow_late_submission = cint(allow_late) if allow_late is not None else 1

		group_submission = data.get("group_submission")
		delivery.group_submission = cint(group_submission) if group_submission is not None else 0

		if data.get("grading_mode"):
			delivery.grading_mode = data["grading_mode"]
		if data.get("grading_mode") == "Points":
			delivery.max_points = data["max_points"]
		if data.get("grade_scale"):
			delivery.grade_scale = data["grade_scale"]

		delivery.insert()
	except Exception:
		frappe.db.rollback(save_point="create_task_and_delivery")
		raise

	return {
		"task": task.name,
		"task_delivery": delivery.name,
	}
