# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.curriculum import planning


def execute():
    if not frappe.db.table_exists("Unit Plan") or not frappe.db.table_exists("Program"):
        return
    if not frappe.db.table_exists("Program Course"):
        return

    course_by_course_plan = _course_by_course_plan()
    existing_programs, archived_programs = _program_state()
    linked_program_courses = _linked_program_courses()

    unit_rows = frappe.get_all(
        "Unit Plan",
        fields=["name", "course_plan", "course", "program"],
        order_by="creation asc, name asc",
        limit=0,
    )
    for row in unit_rows or []:
        _normalize_unit_program(
            row=row,
            course_by_course_plan=course_by_course_plan,
            existing_programs=existing_programs,
            archived_programs=archived_programs,
            linked_program_courses=linked_program_courses,
        )


def _course_by_course_plan() -> dict[str, str]:
    if not frappe.db.table_exists("Course Plan"):
        return {}
    rows = frappe.get_all(
        "Course Plan",
        fields=["name", "course"],
        limit=0,
    )
    return {
        planning.normalize_text(row.get("name")): planning.normalize_text(row.get("course"))
        for row in rows or []
        if planning.normalize_text(row.get("name")) and planning.normalize_text(row.get("course"))
    }


def _program_state() -> tuple[set[str], set[str]]:
    rows = frappe.get_all(
        "Program",
        fields=["name", "archive"],
        limit=0,
    )
    existing_programs: set[str] = set()
    archived_programs: set[str] = set()
    for row in rows or []:
        program_name = planning.normalize_text(row.get("name"))
        if not program_name:
            continue
        existing_programs.add(program_name)
        if int(row.get("archive") or 0):
            archived_programs.add(program_name)
    return existing_programs, archived_programs


def _linked_program_courses() -> set[tuple[str, str]]:
    rows = frappe.get_all(
        "Program Course",
        filters={"parenttype": "Program", "parentfield": "courses"},
        fields=["parent", "course"],
        limit=0,
    )
    return {
        (planning.normalize_text(row.get("parent")), planning.normalize_text(row.get("course")))
        for row in rows or []
        if planning.normalize_text(row.get("parent")) and planning.normalize_text(row.get("course"))
    }


def _normalize_unit_program(
    *,
    row: dict,
    course_by_course_plan: dict[str, str],
    existing_programs: set[str],
    archived_programs: set[str],
    linked_program_courses: set[tuple[str, str]],
) -> None:
    unit_name = planning.normalize_text(row.get("name"))
    program_name = planning.normalize_text(row.get("program"))
    if not unit_name or not program_name:
        return

    if program_name not in existing_programs or program_name in archived_programs:
        frappe.db.set_value("Unit Plan", unit_name, {"program": None}, update_modified=False)
        return

    course_name = planning.normalize_text(row.get("course")) or course_by_course_plan.get(
        planning.normalize_text(row.get("course_plan"))
    )
    if course_name and (program_name, course_name) not in linked_program_courses:
        frappe.db.set_value("Unit Plan", unit_name, {"program": None}, update_modified=False)
