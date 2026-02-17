# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/task_delivery_service.py

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import now


def get_delivery_context(student_group):
    if not student_group:
        frappe.throw(_("Student Group is required for Task Delivery."))

    context = (
        frappe.db.get_value(
            "Student Group",
            student_group,
            ["course", "academic_year", "school", "program"],
            as_dict=True,
        )
        or {}
    )

    if not context:
        frappe.throw(_("Student Group context could not be resolved."))

    return context


def get_eligible_students(student_group):
    if not student_group:
        return []

    rows = frappe.db.get_values(
        "Student Group Student",
        {
            "parent": student_group,
            "parenttype": "Student Group",
            "active": 1,
        },
        "student",
        as_list=True,
    )
    return [row[0] for row in rows if row and row[0]]


def bulk_create_outcomes(delivery, students, context=None):
    if not students:
        return 0

    existing = frappe.db.get_values(
        "Task Outcome",
        {"task_delivery": delivery.name},
        "student",
        as_list=True,
    )
    existing_students = {row[0] for row in existing if row and row[0]}
    new_students = [student for student in students if student not in existing_students]
    if not new_students:
        return 0

    context = context or get_delivery_context(delivery.student_group)
    submission_status, grading_status = _initial_statuses(delivery)

    meta = frappe.get_meta("Task Outcome")
    fields = [
        "name",
        "task_delivery",
        "task",
        "student",
        "student_group",
        "course",
        "academic_year",
        "school",
        "grade_scale",
        "submission_status",
        "grading_status",
        "docstatus",
        "owner",
        "creation",
        "modified",
        "modified_by",
    ]
    if meta.get_field("program"):
        fields.append("program")
    if meta.get_field("course_group"):
        fields.append("course_group")
    if not meta.get_field("grade_scale"):
        fields.remove("grade_scale")

    timestamp = now()
    owner = frappe.session.user
    name_pattern = meta.autoname or "format:TOU-{YYYY}-{MM}-{#####}"

    values = []
    for student in new_students:
        row = {
            "name": make_autoname(name_pattern),
            "task_delivery": delivery.name,
            "task": delivery.task,
            "student": student,
            "student_group": delivery.student_group,
            "course": context.get("course"),
            "academic_year": context.get("academic_year"),
            "school": context.get("school"),
            "grade_scale": delivery.grade_scale if "grade_scale" in fields else None,
            "submission_status": submission_status,
            "grading_status": grading_status,
            "docstatus": 0,
            "owner": owner,
            "creation": timestamp,
            "modified": timestamp,
            "modified_by": owner,
        }

        if "program" in fields:
            row["program"] = context.get("program")
        if "course_group" in fields:
            row["course_group"] = context.get("course_group")

        values.append([row.get(field) for field in fields])

    frappe.db.bulk_insert("Task Outcome", fields, values)
    return len(values)


def resolve_or_create_lesson_instance(delivery, explicit_context=None):
    if delivery.lesson_instance:
        return delivery.lesson_instance

    context = explicit_context or {}
    if not context:
        return None

    lesson = context.get("lesson")
    lesson_activity = context.get("lesson_activity")
    if not lesson and not lesson_activity:
        return None

    instance_type = context.get("instance_type") or "Async Learning Event"
    filters = {
        "student_group": delivery.student_group,
        "instance_type": instance_type,
    }
    if lesson:
        filters["lesson"] = lesson
    if lesson_activity:
        filters["lesson_activity"] = lesson_activity

    existing = frappe.db.get_value("Lesson Instance", filters, "name")
    if existing:
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "Lesson Instance",
            "lesson": lesson,
            "lesson_activity": lesson_activity,
            "student_group": delivery.student_group,
            "instance_type": instance_type,
            "created_from": "Task_delivery",
            "created_by": frappe.session.user,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _initial_statuses(delivery):
    if delivery.delivery_mode == "Assign Only":
        return "Not Required", "Not Applicable"
    if delivery.delivery_mode == "Collect Work":
        return "Not Submitted", "Not Applicable"
    if delivery.delivery_mode == "Assess":
        if delivery.requires_submission:
            return "Not Submitted", "Not Started"
        return "Not Required", "Not Started"
    return "Not Required", "Not Applicable"


def create_delivery(payload):
    if not payload:
        frappe.throw(_("Delivery payload is required."))

    if isinstance(payload, str):
        payload = frappe.parse_json(payload)

    if not isinstance(payload, dict):
        frappe.throw(_("Delivery payload must be a dict."))
    if payload.get("group_submission") in (1, "1", True):
        frappe.throw(_("Group submission is paused: subgroup model not implemented."))

    doc = frappe.new_doc("Task Delivery")

    if payload.get("group_submission"):
        frappe.throw(_("Group submission is currently disabled pending subgroup model implementation."))

    allowed_fields = {
        "task",
        "student_group",
        "delivery_mode",
        "grading_mode",
        "max_points",
        "grade_scale",
        "rubric_scoring_strategy",
        "available_from",
        "due_date",
        "lock_date",
        # "group_submission", # Explicitly commented out/handled above
        "allow_late_submission",
        "lesson_instance",
    }
    for field, value in payload.items():
        if field in allowed_fields:
            setattr(doc, field, value)

    doc.insert(ignore_permissions=True)
    doc.submit()

    outcome_count = frappe.db.count("Task Outcome", {"task_delivery": doc.name})
    return {
        "task_delivery": doc.name,
        "outcomes_created": outcome_count,
    }
