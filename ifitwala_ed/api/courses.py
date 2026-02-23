# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def _get_student_name_for_user(user: str) -> str | None:
    """Map portal user → Student by email (lightweight, indexed)"""
    return frappe.db.get_value("Student", {"student_email": user}, "name")


def _get_academic_years(student_name: str) -> list[str]:
    """Distinct years from Program Enrollment for this student, newest first (single indexed scan)"""
    rows = frappe.db.sql(
        """
    SELECT DISTINCT academic_year
    FROM `tabProgram Enrollment`
    WHERE student = %s
    ORDER BY academic_year DESC
    """,
        (student_name,),
        as_dict=False,
    )
    return [r[0] for r in rows if r and r[0]]


def _get_courses_for_year(student_name: str, academic_year: str) -> list[dict]:
    rows = frappe.db.sql(
        """
        SELECT
            pec.course,
            COALESCE(pec.course_name, c.course_name) AS course_name,
            c.course_group,
            c.course_image
        FROM `tabProgram Enrollment Course` pec
        JOIN `tabProgram Enrollment` pe ON pec.parent = pe.name
        LEFT JOIN `tabCourse` c ON c.name = pec.course
        WHERE pe.student = %s
          AND pe.academic_year = %s
          AND COALESCE(pec.status, 'Enrolled') <> 'Dropped'
        ORDER BY COALESCE(pec.course_name, pec.course)
        """,
        (student_name, academic_year),
        as_dict=True,
    )
    # Ensure we have a valid image URL; otherwise fall back to placeholder
    placeholder = "/assets/ifitwala_ed/images/course_placeholder.jpg"

    def _safe_url(url: str | None) -> str:
        # Accept absolute /files/* or /assets/* URLs; otherwise fall back
        if url and isinstance(url, str) and (url.startswith("/files/") or url.startswith("/assets/")):
            return url
        return placeholder

    courses = []
    for r in rows:
        course = r.get("course")
        if not course:
            continue
        courses.append(
            {
                "course": course,
                "course_name": r.get("course_name") or course,
                "course_group": r.get("course_group"),
                "course_image": _safe_url(r.get("course_image")),
                "href": {"name": "student-course-detail", "params": {"course_id": course}},
            }
        )
    return courses


@frappe.whitelist()
def get_courses_data(academic_year: str | None = None) -> dict:
    """
    Fetch courses data for the logged-in student.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to view this page."), frappe.AuthenticationError)

    roles = set(frappe.get_roles(frappe.session.user))
    student_name = _get_student_name_for_user(frappe.session.user) if "Student" in roles else None
    if not student_name:
        return {
            "academic_years": [],
            "selected_year": None,
            "courses": [],
            "error": _("No student profile linked to this login yet."),
        }

    years = _get_academic_years(student_name)

    selected = academic_year
    if not selected or selected not in years:
        selected = years[0] if years else None

    courses = []
    if selected:
        courses = _get_courses_for_year(student_name, selected)

    return {
        "academic_years": years,
        "selected_year": selected,
        "courses": courses,
    }
