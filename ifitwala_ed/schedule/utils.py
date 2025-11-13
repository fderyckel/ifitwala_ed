# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/utils.py

import frappe
from frappe import _


# This utility function is used to fetch the current courses for a student on the portal.
def get_current_courses():
    """
    Optimized version: Fetch enrolled courses for the logged-in student
    using direct SQL joins. Avoids multiple roundtrips and ORM overhead.
    """
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this page."), frappe.PermissionError)

    student = frappe.db.get_value("Student", {"student_email": frappe.session.user}, "name")
    if not student:
        frappe.throw(_("Student profile not found. Please contact the administrator."))

    query = """
        SELECT
            pec.name AS enrollment_id,
            pec.course AS course,
            c.course_name,
            c.course_group,
            c.course_image
        FROM `tabProgram Enrollment Course` pec
        INNER JOIN `tabProgram Enrollment` pe ON pe.name = pec.parent
        INNER JOIN `tabCourse` c ON c.name = pec.course
        WHERE pe.student = %s
          AND pe.status = 1
          AND pec.status = 'Enrolled'
    """
    results = frappe.db.sql(query, (student,), as_dict=True)
    return results
