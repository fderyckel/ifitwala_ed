from __future__ import annotations

from collections.abc import Iterable

import frappe
from frappe import _

ORDER_STEP = 10


def normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def normalize_long_text(value: str | None) -> str | None:
    text = normalize_text(value)
    return text or None


def get_course_plan_row(course_plan: str) -> dict:
    row = frappe.db.get_value(
        "Course Plan",
        course_plan,
        ["name", "title", "course", "school", "academic_year", "cycle_label", "plan_status"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Course Plan not found."))
    return row


def get_student_group_row(student_group: str) -> dict:
    row = frappe.db.get_value(
        "Student Group",
        student_group,
        ["name", "student_group_name", "student_group_abbreviation", "course", "academic_year", "school"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Student Group not found."))
    return row


def get_unit_plan_rows(course_plan: str) -> list[dict]:
    return frappe.get_all(
        "Unit Plan",
        filters={"course_plan": course_plan, "unit_status": ["!=", "Archived"]},
        fields=[
            "name",
            "title",
            "course_plan",
            "course",
            "program",
            "unit_code",
            "unit_order",
            "unit_status",
            "version",
            "duration",
            "estimated_duration",
            "is_published",
            "overview",
            "essential_understanding",
            "misconceptions",
            "content",
            "skills",
            "concepts",
        ],
        order_by="unit_order asc, creation asc",
        limit=0,
    )


def next_unit_order(course_plan: str) -> int:
    current = frappe.db.sql(
        """
        SELECT COALESCE(MAX(unit_order), 0)
        FROM `tabUnit Plan`
        WHERE course_plan = %s
        """,
        (course_plan,),
        as_list=True,
    )[0][0]
    return int(current or 0) + ORDER_STEP


def next_session_sequence(class_teaching_plan: str, unit_plan: str | None = None) -> int:
    filters = {"class_teaching_plan": class_teaching_plan}
    if unit_plan:
        filters["unit_plan"] = unit_plan
    current = frappe.db.get_value("Class Session", filters, "MAX(sequence_index)")
    return int(current or 0) + ORDER_STEP


def build_class_teaching_plan_title(group_row: dict, course_plan_row: dict) -> str:
    label = normalize_text(group_row.get("student_group_name")) or normalize_text(group_row.get("name"))
    plan_title = normalize_text(course_plan_row.get("title")) or normalize_text(course_plan_row.get("name"))
    return f"{label} · {plan_title}"


def sync_class_teaching_plan_units(doc) -> None:
    unit_rows = get_unit_plan_rows(doc.course_plan)
    if not unit_rows:
        doc.set("units", [])
        return

    existing = {
        normalize_text(row.unit_plan): row
        for row in (doc.get("units") or [])
        if normalize_text(getattr(row, "unit_plan", None))
    }

    refreshed = []
    for unit in unit_rows:
        cached = existing.get(unit["name"])
        refreshed.append(
            {
                "unit_plan": unit["name"],
                "unit_title": unit.get("title"),
                "unit_order": unit.get("unit_order"),
                "governed_required": 1,
                "pacing_status": getattr(cached, "pacing_status", None) or "Not Started",
                "teacher_focus": getattr(cached, "teacher_focus", None),
                "pacing_note": getattr(cached, "pacing_note", None),
                "prior_to_the_unit": getattr(cached, "prior_to_the_unit", None),
                "during_the_unit": getattr(cached, "during_the_unit", None),
                "what_work_well": getattr(cached, "what_work_well", None),
                "what_didnt_work_well": getattr(cached, "what_didnt_work_well", None),
                "changes_suggestions": getattr(cached, "changes_suggestions", None),
            }
        )

    doc.set("units", refreshed)


def sync_all_class_teaching_plans(course_plan: str) -> None:
    course_plan_name = normalize_text(course_plan)
    if not course_plan_name:
        return

    plan_names = frappe.get_all(
        "Class Teaching Plan",
        filters={"course_plan": course_plan_name},
        pluck="name",
        limit=0,
    )
    for plan_name in plan_names or []:
        doc = frappe.get_doc("Class Teaching Plan", plan_name)
        sync_class_teaching_plan_units(doc)
        doc.save(ignore_permissions=True)


def replace_session_activities(doc, rows: Iterable[dict] | None) -> None:
    sanitized: list[dict] = []
    for idx, row in enumerate(rows or [], start=1):
        title = normalize_text((row or {}).get("title"))
        if not title:
            continue
        sequence_index = (row or {}).get("sequence_index")
        sanitized.append(
            {
                "title": title,
                "activity_type": normalize_text((row or {}).get("activity_type")) or "Other",
                "estimated_minutes": (row or {}).get("estimated_minutes"),
                "sequence_index": int(sequence_index) if sequence_index not in (None, "") else idx * ORDER_STEP,
                "student_direction": normalize_long_text((row or {}).get("student_direction")),
                "teacher_prompt": normalize_long_text((row or {}).get("teacher_prompt")),
                "resource_note": normalize_long_text((row or {}).get("resource_note")),
            }
        )
    doc.set("activities", sanitized)
