# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/task_delivery_service.py

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import now

from ifitwala_ed.assessment.check_flags import is_checked


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

    return frappe.get_all(
        "Student Group Student",
        filters={
            "parent": student_group,
            "parenttype": "Student Group",
            "active": 1,
        },
        pluck="student",
        limit=0,
    )


def resolve_planning_context(student_group, class_teaching_plan=None, class_session=None):
    student_group = (student_group or "").strip()
    class_teaching_plan = (class_teaching_plan or "").strip()
    class_session = (class_session or "").strip()
    if not student_group:
        frappe.throw(_("Student Group is required for Task Delivery."))

    session_row = None
    if class_session:
        session_row = frappe.db.get_value(
            "Class Session",
            class_session,
            ["name", "class_teaching_plan", "student_group", "course", "academic_year", "unit_plan"],
            as_dict=True,
        )
        if not session_row:
            frappe.throw(_("Class Session not found."))
        if (session_row.get("student_group") or "").strip() != student_group:
            frappe.throw(_("Selected class session does not belong to this class."))
        class_teaching_plan = class_teaching_plan or (session_row.get("class_teaching_plan") or "").strip()

    if not class_teaching_plan:
        active_rows = frappe.get_all(
            "Class Teaching Plan",
            filters={"student_group": student_group, "planning_status": "Active"},
            fields=["name"],
            order_by="modified desc, creation desc",
            limit=2,
        )
        if not active_rows:
            frappe.throw(_("This class needs an active Class Teaching Plan before assigned work can be created."))
        if len(active_rows) > 1:
            frappe.throw(_("Select the Class Teaching Plan for this class before creating assigned work."))
        class_teaching_plan = active_rows[0]["name"]

    plan_row = frappe.db.get_value(
        "Class Teaching Plan",
        class_teaching_plan,
        ["name", "student_group", "course_plan", "course", "academic_year", "planning_status"],
        as_dict=True,
    )
    if not plan_row:
        frappe.throw(_("Class Teaching Plan not found."))
    if (plan_row.get("student_group") or "").strip() != student_group:
        frappe.throw(_("Selected Class Teaching Plan does not belong to this class."))
    if (plan_row.get("planning_status") or "").strip() == "Archived":
        frappe.throw(_("Archived Class Teaching Plans cannot receive new assigned work."))

    if session_row and (session_row.get("class_teaching_plan") or "").strip() != class_teaching_plan:
        frappe.throw(_("Selected class session does not belong to this Class Teaching Plan."))

    return {
        "class_teaching_plan": class_teaching_plan,
        "class_session": class_session or None,
        "course_plan": (plan_row.get("course_plan") or "").strip() or None,
        "course": (plan_row.get("course") or "").strip() or None,
        "academic_year": (plan_row.get("academic_year") or "").strip() or None,
        "unit_plan": (session_row or {}).get("unit_plan") if session_row else None,
    }


def bulk_create_outcomes(delivery, students, context=None):
    if not students:
        return 0

    existing = frappe.get_all(
        "Task Outcome",
        filters={"task_delivery": delivery.name},
        pluck="student",
        limit=0,
    )
    existing_students = {student for student in existing if student}
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
    if is_checked(payload.get("group_submission")):
        frappe.throw(_("Group submission is paused: subgroup model not implemented."))

    planning_context = resolve_planning_context(
        payload.get("student_group"),
        payload.get("class_teaching_plan"),
        payload.get("class_session"),
    )

    doc = frappe.new_doc("Task Delivery")

    allowed_fields = {
        "task",
        "student_group",
        "class_teaching_plan",
        "delivery_mode",
        "grading_mode",
        "allow_feedback",
        "max_points",
        "grade_scale",
        "rubric_scoring_strategy",
        "available_from",
        "due_date",
        "lock_date",
        # "group_submission", # Explicitly commented out/handled above
        "allow_late_submission",
        "class_session",
    }
    for field, value in payload.items():
        if field in allowed_fields:
            setattr(doc, field, value)

    doc.class_teaching_plan = planning_context["class_teaching_plan"]
    if planning_context.get("class_session"):
        doc.class_session = planning_context["class_session"]

    doc.insert(ignore_permissions=True)
    doc.flags.ignore_permissions = True
    doc.submit()
    doc.materialize_roster()

    outcome_count = frappe.db.count("Task Outcome", {"task_delivery": doc.name})
    return {
        "task_delivery": doc.name,
        "outcomes_created": outcome_count,
    }
