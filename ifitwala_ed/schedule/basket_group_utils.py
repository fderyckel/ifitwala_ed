# ifitwala_ed/schedule/basket_group_utils.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def _normalize_group_rows(rows: list[dict] | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in rows or []:
        course = ((row or {}).get("course") or "").strip()
        basket_group = ((row or {}).get("basket_group") or "").strip()
        if not course or not basket_group:
            continue
        if course not in out:
            out[course] = []
        if basket_group not in out[course]:
            out[course].append(basket_group)
    return out


def get_program_course_basket_group_map(program: str) -> dict[str, list[str]]:
    if not program or not frappe.db.table_exists("Program Course Basket Group"):
        return {}

    rows = frappe.get_all(
        "Program Course Basket Group",
        filters={"parent": program, "parenttype": "Program"},
        fields=["course", "basket_group"],
        order_by="idx asc",
        limit_page_length=5000,
    )
    return _normalize_group_rows(rows)


def get_offering_course_basket_group_map(program_offering: str) -> dict[str, list[str]]:
    if not program_offering or not frappe.db.table_exists("Program Offering Course Basket Group"):
        return {}

    rows = frappe.get_all(
        "Program Offering Course Basket Group",
        filters={"parent": program_offering, "parenttype": "Program Offering"},
        fields=["course", "basket_group"],
        order_by="idx asc",
        limit_page_length=5000,
    )
    return _normalize_group_rows(rows)


def get_program_course_semantics(program: str) -> dict[str, dict]:
    if not program:
        return {}

    rows = frappe.get_all(
        "Program Course",
        filters={"parent": program, "parenttype": "Program"},
        fields=["course", "required", "repeatable", "max_attempts", "level"],
        order_by="idx asc",
        limit_page_length=5000,
    )
    basket_groups = get_program_course_basket_group_map(program)

    out: dict[str, dict] = {}
    for row in rows:
        course = (row.get("course") or "").strip()
        if not course:
            continue
        normalized = dict(row)
        normalized["required"] = 1 if row.get("required") else 0
        normalized["basket_groups"] = list(basket_groups.get(course) or [])
        out[course] = normalized
    return out


def get_offering_course_semantics(program_offering: str) -> dict[str, dict]:
    if not program_offering:
        return {}

    rows = frappe.get_all(
        "Program Offering Course",
        filters={"parent": program_offering, "parenttype": "Program Offering"},
        fields=[
            "course",
            "course_name",
            "required",
            "start_academic_year",
            "start_academic_term",
            "from_date",
            "end_academic_year",
            "end_academic_term",
            "to_date",
            "capacity",
            "waitlist_enabled",
            "reserved_seats",
            "grade_scale",
        ],
        order_by="idx asc",
        limit_page_length=5000,
    )
    basket_groups = get_offering_course_basket_group_map(program_offering)

    out: dict[str, dict] = {}
    for row in rows:
        course = (row.get("course") or "").strip()
        if not course:
            continue

        normalized = out.get(course)
        if not normalized:
            normalized = dict(row)
            normalized["required"] = 1 if row.get("required") else 0
            normalized["basket_groups"] = list(basket_groups.get(course) or [])
            out[course] = normalized
            continue

        normalized["required"] = 1 if normalized.get("required") or row.get("required") else 0
        if not (normalized.get("course_name") or "").strip() and (row.get("course_name") or "").strip():
            normalized["course_name"] = row.get("course_name")
        if normalized.get("capacity") is None and row.get("capacity") is not None:
            normalized["capacity"] = row.get("capacity")
        if not normalized.get("waitlist_enabled") and row.get("waitlist_enabled"):
            normalized["waitlist_enabled"] = row.get("waitlist_enabled")
        if not normalized.get("reserved_seats") and row.get("reserved_seats"):
            normalized["reserved_seats"] = row.get("reserved_seats")
        if not (normalized.get("grade_scale") or "").strip() and (row.get("grade_scale") or "").strip():
            normalized["grade_scale"] = row.get("grade_scale")

    for course, normalized in out.items():
        normalized["basket_groups"] = list(basket_groups.get(course) or [])

    return out
