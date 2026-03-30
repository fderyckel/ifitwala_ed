# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import cstr

from ifitwala_ed.schedule.enrollment_request_utils import _resolve_materialization_course_terms


def execute():
    if not frappe.db.table_exists("Program Enrollment") or not frappe.db.table_exists("Program Enrollment Course"):
        return

    enrollment_names = frappe.db.sql(
        """
        SELECT DISTINCT pe.name
        FROM `tabProgram Enrollment` pe
        INNER JOIN `tabProgram Enrollment Course` pec
            ON pec.parent = pe.name
            AND pec.parenttype = 'Program Enrollment'
        WHERE pe.enrollment_source = 'Request'
            AND IFNULL(pe.program_enrollment_request, '') != ''
            AND (IFNULL(pec.term_start, '') = '' OR IFNULL(pec.term_end, '') = '')
        """,
        as_list=True,
    )

    for row in enrollment_names or []:
        enrollment_name = cstr((row or [None])[0]).strip()
        if not enrollment_name:
            continue
        _backfill_enrollment_terms(enrollment_name)


def _backfill_enrollment_terms(enrollment_name: str) -> int:
    enrollment = frappe.get_doc("Program Enrollment", enrollment_name)
    missing_courses = sorted(
        {
            cstr(getattr(row, "course", None)).strip()
            for row in (enrollment.courses or [])
            if cstr(getattr(row, "course", None)).strip()
            and (not cstr(getattr(row, "term_start", None)).strip() or not cstr(getattr(row, "term_end", None)).strip())
        }
    )
    if not missing_courses:
        return 0

    resolved_terms = _resolve_materialization_course_terms(
        program_offering=enrollment.program_offering,
        academic_year=enrollment.academic_year,
        school=enrollment.school,
        courses=missing_courses,
    )

    updated_rows = 0
    for row in enrollment.courses or []:
        course = cstr(getattr(row, "course", None)).strip()
        if not course:
            continue

        term_info = resolved_terms.get(course) or {}
        changed = False
        if not cstr(getattr(row, "term_start", None)).strip() and cstr(term_info.get("term_start")).strip():
            row.term_start = term_info["term_start"]
            changed = True
        if not cstr(getattr(row, "term_end", None)).strip() and cstr(term_info.get("term_end")).strip():
            row.term_end = term_info["term_end"]
            changed = True
        if changed:
            updated_rows += 1

    if updated_rows:
        enrollment.save(ignore_permissions=True)

    return updated_rows
