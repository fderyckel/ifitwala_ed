# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict

import frappe

from ifitwala_ed.api import teaching_plans as teaching_plans_api
from ifitwala_ed.curriculum import planning
from ifitwala_ed.curriculum.doctype.course_plan.course_plan import (
    ACTIVATION_MODE_ACADEMIC_YEAR_START,
    ACTIVATION_MODE_MANUAL,
    _resolve_course_school,
)


def execute():
    if not frappe.db.table_exists("Course Plan") or not frappe.db.table_exists("Academic Year"):
        return

    has_course_table = frappe.db.table_exists("Course")
    academic_year_rows = frappe.get_all(
        "Academic Year",
        fields=["name", "academic_year_name", "school"],
        order_by="creation asc, name asc",
        limit=0,
    )
    academic_years_by_name: dict[str, dict[str, str]] = {}
    academic_years_by_label: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in academic_year_rows or []:
        academic_year_name = planning.normalize_text(row.get("name"))
        if not academic_year_name:
            continue
        normalized_row = {
            "name": academic_year_name,
            "academic_year_name": planning.normalize_text(row.get("academic_year_name")),
            "school": planning.normalize_text(row.get("school")),
        }
        academic_years_by_name[academic_year_name] = normalized_row
        if normalized_row["academic_year_name"]:
            academic_years_by_label[normalized_row["academic_year_name"]].append(normalized_row)

    course_plan_rows = frappe.get_all(
        "Course Plan",
        fields=["name", "course", "school", "academic_year", "activation_mode"],
        order_by="creation asc, name asc",
        limit=0,
    )
    for row in course_plan_rows or []:
        _normalize_course_plan_academic_year_scope(
            row=row,
            has_course_table=has_course_table,
            academic_years_by_name=academic_years_by_name,
            academic_years_by_label=academic_years_by_label,
        )


def _normalize_course_plan_academic_year_scope(
    *,
    row: dict,
    has_course_table: bool,
    academic_years_by_name: dict[str, dict[str, str]],
    academic_years_by_label: dict[str, list[dict[str, str]]],
) -> None:
    course_plan_name = planning.normalize_text(row.get("name"))
    current_academic_year = planning.normalize_text(row.get("academic_year"))
    if not course_plan_name or not current_academic_year:
        return

    course_school = (
        planning.normalize_text(
            _resolve_course_school(
                planning.normalize_text(row.get("course")),
                fallback=planning.normalize_text(row.get("school")) or None,
            )
        )
        if has_course_table
        else planning.normalize_text(row.get("school"))
    )
    if not course_school:
        return

    allowed_scope = {
        planning.normalize_text(scope_school)
        for scope_school in (teaching_plans_api._academic_year_scope_for_school(course_school) or [])
        if planning.normalize_text(scope_school)
    }
    if not allowed_scope:
        return

    current_row = academic_years_by_name.get(current_academic_year)
    if current_row and planning.normalize_text(current_row.get("school")) in allowed_scope:
        return

    academic_year_label = (
        planning.normalize_text((current_row or {}).get("academic_year_name")) or current_academic_year
    )
    candidates = [
        candidate
        for candidate in academic_years_by_label.get(academic_year_label, [])
        if planning.normalize_text(candidate.get("school")) in allowed_scope
    ]

    updates: dict[str, str | None] = {}
    if len(candidates) == 1:
        target_name = planning.normalize_text(candidates[0].get("name"))
        if target_name and target_name != current_academic_year:
            updates["academic_year"] = target_name
    else:
        updates["academic_year"] = None
        if planning.normalize_text(row.get("activation_mode")) == ACTIVATION_MODE_ACADEMIC_YEAR_START:
            updates["activation_mode"] = ACTIVATION_MODE_MANUAL

    if updates:
        frappe.db.set_value("Course Plan", course_plan_name, updates, update_modified=False)
