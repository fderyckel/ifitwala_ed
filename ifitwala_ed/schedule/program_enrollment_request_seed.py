# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint

NON_TERMINAL_REQUEST_STATUSES = {"Draft", "Submitted", "Under Review", "Approved"}


def get_target_enrollments(*, student_ids: list[str], program_offering: str, academic_year: str) -> set[str]:
    names = sorted({(name or "").strip() for name in (student_ids or []) if (name or "").strip()})
    if not names or not program_offering or not academic_year:
        return set()

    return set(
        frappe.get_all(
            "Program Enrollment",
            filters={
                "program_offering": program_offering,
                "academic_year": academic_year,
                "student": ["in", names],
            },
            pluck="student",
        )
    )


def get_target_request_map(*, student_ids: list[str], program_offering: str, academic_year: str) -> dict[str, dict]:
    names = sorted({(name or "").strip() for name in (student_ids or []) if (name or "").strip()})
    if not names or not program_offering or not academic_year:
        return {}

    rows = frappe.get_all(
        "Program Enrollment Request",
        filters={
            "student": ["in", names],
            "program_offering": program_offering,
            "academic_year": academic_year,
            "status": ["in", list(NON_TERMINAL_REQUEST_STATUSES)],
        },
        fields=[
            "name",
            "student",
            "status",
            "validation_status",
            "requires_override",
            "selection_window",
            "modified",
        ],
        order_by="modified desc",
        limit=max(200, len(names) * 3),
    )

    output: dict[str, dict] = {}
    for row in rows or []:
        student = (row.get("student") or "").strip()
        if not student or student in output:
            continue
        output[student] = row
    return output


def get_source_enrollment_map(
    *,
    student_ids: list[str],
    program_offering: str,
    academic_year: str,
) -> dict[str, dict]:
    names = sorted({(name or "").strip() for name in (student_ids or []) if (name or "").strip()})
    if not names or not program_offering or not academic_year:
        return {}

    source_rows = frappe.get_all(
        "Program Enrollment",
        filters={
            "student": ["in", names],
            "program_offering": program_offering,
            "academic_year": academic_year,
        },
        fields=["name", "student"],
        order_by="modified desc",
        limit=max(200, len(names) * 3),
    )

    output: dict[str, dict] = {}
    parent_to_student: dict[str, str] = {}
    for row in source_rows or []:
        student = (row.get("student") or "").strip()
        parent = (row.get("name") or "").strip()
        if not student or not parent or student in output:
            continue
        output[student] = {"name": parent, "courses": []}
        parent_to_student[parent] = student

    if not parent_to_student:
        return output

    course_rows = frappe.get_all(
        "Program Enrollment Course",
        filters={
            "parent": ["in", list(parent_to_student.keys())],
            "parenttype": "Program Enrollment",
        },
        fields=["parent", "course", "status", "credited_basket_group"],
        order_by="idx asc",
        limit=max(500, len(parent_to_student) * 20),
    )
    for row in course_rows or []:
        parent = (row.get("parent") or "").strip()
        student = parent_to_student.get(parent)
        if not student:
            continue
        output.setdefault(student, {"name": parent, "courses": []})["courses"].append(row)

    return output


def target_courses_by_group(target_semantics: dict[str, dict]) -> dict[str, list[str]]:
    output: dict[str, list[str]] = defaultdict(list)
    for course, semantics in (target_semantics or {}).items():
        if cint((semantics or {}).get("required")):
            continue
        for basket_group in (semantics or {}).get("basket_groups") or []:
            output[basket_group].append(course)
    return output


def resolve_applied_basket_group(*, allowed_groups: list[str], source_group: str, allow_blank: bool) -> str:
    groups = [group for group in (allowed_groups or []) if group]
    if not groups:
        return ""
    if len(groups) == 1:
        return groups[0]
    if source_group and source_group in groups:
        return source_group
    return "" if allow_blank else None


def build_request_rows_for_student(
    *,
    source_enrollment: dict | None,
    target_semantics: dict[str, dict],
    target_courses_by_group_map: dict[str, list[str]],
) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    seen: set[str] = set()
    review_notes: list[str] = []

    for course, semantics in (target_semantics or {}).items():
        if not cint((semantics or {}).get("required")):
            continue
        rows.append(
            {
                "course": course,
                "required": 1,
                "applied_basket_group": "",
                "choice_rank": None,
            }
        )
        seen.add(course)

    for source_row in (source_enrollment or {}).get("courses") or []:
        source_course = (source_row.get("course") or "").strip()
        status = (source_row.get("status") or "").strip()
        source_group = (source_row.get("credited_basket_group") or "").strip()
        if not source_course or status == "Dropped":
            continue

        target_course = None
        applied_group = ""
        allowed_groups: list[str] = []

        if source_course in target_semantics:
            target_course = source_course
            allowed_groups = list((target_semantics.get(target_course) or {}).get("basket_groups") or [])
            applied_group = resolve_applied_basket_group(
                allowed_groups=allowed_groups,
                source_group=source_group,
                allow_blank=True,
            )
            if len(allowed_groups) > 1 and not applied_group:
                review_notes.append(_("Request needs a basket-group choice for course {0}.").format(source_course))
        elif source_group and len(target_courses_by_group_map.get(source_group) or []) == 1:
            target_course = target_courses_by_group_map[source_group][0]
            allowed_groups = list((target_semantics.get(target_course) or {}).get("basket_groups") or [])
            applied_group = source_group if source_group in allowed_groups else ""

        if not target_course or target_course in seen:
            continue

        semantics = target_semantics.get(target_course) or {}
        if cint(semantics.get("required")):
            continue

        rows.append(
            {
                "course": target_course,
                "required": 0,
                "applied_basket_group": applied_group,
                "choice_rank": None,
            }
        )
        seen.add(target_course)

    return rows, review_notes


def create_draft_request(
    *,
    student: str,
    program_offering: str,
    academic_year: str,
    request_rows: list[dict],
    selection_window: str | None = None,
) -> frappe.model.document.Document:
    if not request_rows:
        frappe.throw(_("At least one request row is required."))

    payload = {
        "doctype": "Program Enrollment Request",
        "student": student,
        "program_offering": program_offering,
        "academic_year": academic_year,
        "status": "Draft",
        "courses": request_rows,
    }
    if selection_window:
        payload["selection_window"] = selection_window

    return frappe.get_doc(payload).insert(ignore_permissions=True)
