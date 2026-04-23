# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

CONTEXT_FIELDS = ("program", "academic_year", "program_offering", "school")


def _is_blank(value) -> bool:
    return not str(value or "").strip()


def _target_log_date(row) -> str | None:
    date_value = str(row.get("date") or "").strip()
    if date_value:
        return date_value

    creation = str(row.get("creation") or "").strip()
    return creation[:10] or None


def execute():
    required_tables = (
        "Student Log",
        "Program Enrollment",
        "Academic Year",
        "Program",
        "Program Offering",
    )
    if any(not frappe.db.table_exists(doctype) for doctype in required_tables):
        return

    from ifitwala_ed.students.doctype.student_log.student_log import (
        _get_program_enrollment_context,
        _resolve_student_log_school,
    )

    log_rows = frappe.get_all(
        "Student Log",
        fields=["name", "student", "date", "creation", "program", "academic_year", "program_offering", "school"],
        order_by="creation asc, name asc",
        limit=0,
    )

    context_cache: dict[tuple[str, str | None], dict[str, str | None]] = {}
    school_cache: dict[tuple[str, str | None, str | None], str | None] = {}

    for row in log_rows or []:
        if not any(_is_blank(row.get(fieldname)) for fieldname in CONTEXT_FIELDS):
            continue

        log_name = str(row.get("name") or "").strip()
        student = str(row.get("student") or "").strip()
        if not log_name or not student:
            continue

        target_date = _target_log_date(row)
        context_key = (student, target_date)
        if context_key not in context_cache:
            context_cache[context_key] = (
                _get_program_enrollment_context(
                    student,
                    on_date=target_date,
                    require_unique=True,
                )
                or {}
            )
        context = context_cache[context_key]

        updates = {}
        for fieldname in CONTEXT_FIELDS:
            if _is_blank(row.get(fieldname)) and context.get(fieldname):
                updates[fieldname] = context[fieldname]

        if _is_blank(row.get("school")) and not updates.get("school"):
            academic_year = updates.get("academic_year") or row.get("academic_year")
            program_offering = updates.get("program_offering") or row.get("program_offering")
            school_key = (
                student,
                str(academic_year or "").strip() or None,
                str(program_offering or "").strip() or None,
            )
            if school_key not in school_cache:
                school_cache[school_key] = _resolve_student_log_school(
                    student=student,
                    academic_year=school_key[1],
                    program_offering=school_key[2],
                )
            resolved_school = school_cache[school_key]
            if resolved_school:
                updates["school"] = resolved_school

        if updates:
            frappe.db.set_value("Student Log", log_name, updates, update_modified=False)
