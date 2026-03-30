# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/task_creation_service.py

import frappe
from frappe import _

from ifitwala_ed.assessment.check_flags import to_check_value

V1_GRADING_MODES = {"None", "Completion", "Binary", "Points"}


def _parse_options(doctype, fieldname):
    meta = frappe.get_meta(doctype)
    field = meta.get_field(fieldname)
    if not field or not field.options:
        return []
    return [opt.strip() for opt in field.options.split("\n") if opt.strip()]


def _validate_payload(payload: dict) -> dict:
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
        "quiz_question_bank",
        "quiz_question_count",
        "quiz_time_limit_minutes",
        "quiz_max_attempts",
        "quiz_pass_percentage",
    }
    extra = set(payload.keys()) - allowed_keys
    if extra:
        frappe.throw(_("Unsupported payload fields: {fields}").format(fields=", ".join(sorted(extra))))

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
            frappe.throw(_("Invalid task type: {task_type}").format(task_type=task_type))
    if task_type == "Quiz" and not payload.get("quiz_question_bank"):
        frappe.throw(_("Quiz Question Bank is required for quiz tasks."))

    delivery_options = set(_parse_options("Task Delivery", "delivery_mode"))
    if delivery_mode not in delivery_options:
        frappe.throw(_("Invalid delivery mode: {delivery_mode}").format(delivery_mode=delivery_mode))

    grading_mode = payload.get("grading_mode")
    if grading_mode in ("", None):
        grading_mode = None

    if grading_mode is not None and grading_mode not in V1_GRADING_MODES:
        frappe.throw(_("Invalid grading mode for v1: {grading_mode}").format(grading_mode=grading_mode))

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
        "quiz_question_bank": payload.get("quiz_question_bank"),
        "quiz_question_count": payload.get("quiz_question_count"),
        "quiz_time_limit_minutes": payload.get("quiz_time_limit_minutes"),
        "quiz_max_attempts": payload.get("quiz_max_attempts"),
        "quiz_pass_percentage": payload.get("quiz_pass_percentage"),
    }


@frappe.whitelist()
def create_task_and_delivery(
    title=None,
    student_group=None,
    delivery_mode=None,
    instructions=None,
    task_type=None,
    is_template=None,
    available_from=None,
    due_date=None,
    lock_date=None,
    allow_late_submission=None,
    group_submission=None,
    grading_mode=None,
    max_points=None,
    grade_scale=None,
    quiz_question_bank=None,
    quiz_question_count=None,
    quiz_time_limit_minutes=None,
    quiz_max_attempts=None,
    quiz_pass_percentage=None,
    **unexpected,
):

    # Frappe always injects "cmd" into form_dict for /api/method calls.
    # We ignore it explicitly to preserve strict "no unknown keys" for everything else.
    if unexpected:
        unexpected.pop("cmd", None)

    # ✅ enforce “no unknown keys” even though we accept **unexpected to catch them
    if unexpected:
        frappe.throw(_("Unsupported payload fields: {fields}").format(fields=", ".join(sorted(unexpected.keys()))))

    payload = {
        "title": title,
        "instructions": instructions,
        "task_type": task_type,
        "is_template": is_template,
        "student_group": student_group,
        "delivery_mode": delivery_mode,
        "available_from": available_from,
        "due_date": due_date,
        "lock_date": lock_date,
        "allow_late_submission": allow_late_submission,
        "group_submission": group_submission,
        "grading_mode": grading_mode,
        "max_points": max_points,
        "grade_scale": grade_scale,
        "quiz_question_bank": quiz_question_bank,
        "quiz_question_count": quiz_question_count,
        "quiz_time_limit_minutes": quiz_time_limit_minutes,
        "quiz_max_attempts": quiz_max_attempts,
        "quiz_pass_percentage": quiz_pass_percentage,
    }

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
        if data.get("task_type") == "Quiz":
            task.quiz_question_bank = data.get("quiz_question_bank")
            task.quiz_question_count = data.get("quiz_question_count")
            task.quiz_time_limit_minutes = data.get("quiz_time_limit_minutes")
            task.quiz_max_attempts = data.get("quiz_max_attempts")
            task.quiz_pass_percentage = data.get("quiz_pass_percentage")
            task.quiz_shuffle_questions = 1
            task.quiz_shuffle_choices = 1

        task.is_template = to_check_value(data.get("is_template"))

        course = frappe.db.get_value("Student Group", data["student_group"], "course")
        if not course:
            frappe.throw(_("Student group is missing a course."))

        task.default_course = course
        task.default_delivery_mode = data["delivery_mode"]
        task.default_grading_mode = (
            "Points"
            if data.get("task_type") == "Quiz" and data["delivery_mode"] == "Assess"
            else data["grading_mode"] or "None"
        )
        task.default_requires_submission = (
            0 if data.get("task_type") == "Quiz" else 1 if data["delivery_mode"] in ("Collect Work", "Assess") else 0
        )

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
        delivery.allow_late_submission = 1 if allow_late is None else to_check_value(allow_late)

        group_sub = data.get("group_submission")
        delivery.group_submission = to_check_value(group_sub)

        if data.get("grading_mode"):
            delivery.grading_mode = data["grading_mode"]
        if data.get("grading_mode") == "Points":
            delivery.max_points = data["max_points"]
        if data.get("grade_scale"):
            delivery.grade_scale = data["grade_scale"]

        delivery.insert(ignore_permissions=True)
        delivery.flags.ignore_permissions = True
        delivery.submit()
        delivery.materialize_roster()

    except Exception:
        frappe.db.rollback(save_point="create_task_and_delivery")
        raise

    return {
        "task": task.name,
        "task_delivery": delivery.name,
        "outcomes_created": frappe.db.count("Task Outcome", {"task_delivery": delivery.name}),
    }
