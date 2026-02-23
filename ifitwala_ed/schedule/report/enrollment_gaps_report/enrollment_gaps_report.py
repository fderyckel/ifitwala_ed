# Copyright (c) 2025, François de Ryckel and contributors
# License: MIT. See license.txt

# ifitwala_ed/schedule/report/enrollment_gaps_report/enrollment_gaps_report.py

import frappe
from frappe import _

from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def academic_year_link_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Allow picking Academic Years whose `school` is the selected school
    or any of its **ancestors** (covers IIS parent AY when ISS is selected).
    """
    school = (filters or {}).get("school")
    params = {"txt": f"%{txt}%", "start": start, "page_len": page_len}

    if not school:
        # permissive before School is chosen
        return frappe.db.sql(
            """
            SELECT name
            FROM `tabAcademic Year`
            WHERE name LIKE %(txt)s
            ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
            LIMIT %(start)s, %(page_len)s
            """,
            params,
        )

    # Ancestors list already includes self per your util
    scope_schools = tuple(get_ancestor_schools(school) or [school])

    return frappe.db.sql(
        """
        SELECT name
        FROM `tabAcademic Year`
        WHERE school IN %(schools)s
          AND name LIKE %(txt)s
        ORDER BY COALESCE(year_start_date, '0001-01-01') DESC, name DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {**params, "schools": scope_schools},
    )


def execute(filters=None):
    filters = filters or {}
    ay = (filters.get("academic_year") or "").strip()
    school = (filters.get("school") or "").strip()
    if not school:
        frappe.throw(_("Please select a School."))
    if not ay:
        frappe.throw(_("Please select an Academic Year."))

    ay_row = frappe.db.get_value(
        "Academic Year",
        ay,
        ["year_start_date", "year_end_date"],
        as_dict=True,
    )
    if not ay_row:
        frappe.throw(_("Academic Year {0} was not found.").format(ay))
    if not (ay_row.year_start_date and ay_row.year_end_date):
        frappe.throw(_("Academic Year {0} must have both a start date and an end date.").format(ay))

    schools = tuple(get_descendant_schools(school) or [school])

    columns = [
        {"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 170},
        {"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 130},
        {"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 220},
        {"label": _("Program"), "fieldname": "program", "fieldtype": "Link", "options": "Program", "width": 160},
        {"label": _("Course"), "fieldname": "course", "fieldtype": "Link", "options": "Course", "width": 220},
        {"label": _("Term Start"), "fieldname": "term", "fieldtype": "Link", "options": "Term", "width": 150},
        {"label": _("Missing"), "fieldname": "missing", "fieldtype": "Data", "width": 180},
    ]

    data = frappe.db.sql(
        """
        WITH enrollments AS (
            SELECT
                pe.student,
                COALESCE(st.student_full_name, pe.student_name) AS student_name,
                pe.program,
                pe.program_offering,
                pe.academic_year,
                pe.school,
                pec.course,
                pec.term_start
            FROM `tabProgram Enrollment` pe
            INNER JOIN `tabProgram Enrollment Course` pec
                ON pec.parent = pe.name
               AND pec.parenttype = 'Program Enrollment'
               AND COALESCE(pec.status, 'Enrolled') = 'Enrolled'
            LEFT JOIN `tabStudent` st ON st.name = pe.student
            WHERE pe.academic_year = %(ay)s
              AND pe.school IN %(schools)s
        ),
        course_groups AS (
            SELECT DISTINCT
                sgs.student,
                sg.course,
                sg.term,
                sg.program,
                sg.program_offering
            FROM `tabStudent Group` sg
            INNER JOIN `tabStudent Group Student` sgs
                ON sgs.parent = sg.name
               AND sgs.parenttype = 'Student Group'
               AND COALESCE(sgs.active, 1) = 1
            INNER JOIN `tabAcademic Year` sgay ON sgay.name = sg.academic_year
            WHERE sg.status = 'Active'
              AND sg.group_based_on = 'Course'
              AND COALESCE(sgay.year_start_date, %(ay_start)s) <= %(ay_end)s
              AND COALESCE(sgay.year_end_date, %(ay_end)s)   >= %(ay_start)s
        )

        -- (1) In-scope students with NO Program Enrollment in AY
        SELECT
            'Missing Program Enrollment' AS type,
            s.name                       AS student,
            s.student_full_name          AS student_name,
            NULL                         AS program,
            NULL                         AS course,
            NULL                         AS term,
            'Program Enrollment'         AS missing
        FROM `tabStudent` s
        WHERE COALESCE(s.enabled, 1) = 1
          AND EXISTS (
                SELECT 1
                FROM `tabProgram Enrollment` pe_scope
                WHERE pe_scope.student = s.name
                  AND pe_scope.school IN %(schools)s
          )
          AND NOT EXISTS (
                SELECT 1
                FROM `tabProgram Enrollment` pe
                WHERE pe.student = s.name
                  AND pe.academic_year = %(ay)s
          )

        UNION ALL

        -- (2) Enrolled in a course but NOT placed in a matching Course-based SG (term-aware)
        SELECT
            'Missing Student Group' AS type,
            e.student               AS student,
            e.student_name          AS student_name,
            e.program               AS program,
            e.course                AS course,
            e.term_start            AS term,
            'Student Group (Course)' AS missing
        FROM enrollments e
        LEFT JOIN course_groups cg
          ON cg.student = e.student
         AND cg.course = e.course
         AND (
                cg.term IS NULL
             OR e.term_start IS NULL
             OR cg.term = e.term_start
         )
         AND (
                (
                    cg.program_offering IS NOT NULL
                    AND e.program_offering IS NOT NULL
                    AND cg.program_offering = e.program_offering
                )
             OR (
                    (cg.program_offering IS NULL OR e.program_offering IS NULL)
                    AND cg.program = e.program
                )
         )
        WHERE cg.student IS NULL
        ORDER BY 1, 2
        """,
        {
            "ay": ay,
            "schools": schools,
            "ay_start": ay_row.year_start_date,
            "ay_end": ay_row.year_end_date,
        },
        as_dict=True,
    )

    return columns, data
