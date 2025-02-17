# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from ifitwala_ed.schedule.utils import get_current_courses

def get_context(context):
    # Validate that the user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this page."), frappe.PermissionError)
    
    # Ensure the user has the Student role
    user_roles = frappe.get_roles(frappe.session.user)
    if "Student" not in user_roles:
        frappe.throw(_("You are not authorized to access this page."), frappe.PermissionError)
    
    # Fetch the student record using the session email
    student_data = frappe.db.get_value(
        "Student", {"student_email": frappe.session.user},
        ["student_preferred_name", "student_image"],
        as_dict=True
    )
    if not student_data:
        frappe.throw(_("Student profile not found. Please contact the administrator."))
    
    # Populate the context with student information and current courses
    context.student_preferred_name = student_data.get("student_preferred_name", "Student")
    context.student_image = student_data.get("student_image", None)
    context.courses = get_current_courses()
    context.title = "My Courses"
    
    return context
