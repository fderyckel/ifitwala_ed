import frappe
from frappe import _

def get_context(context):
    """
    Prepares the context for the Student Portal (index.html).
    Restricts access to logged-in users with the 'Student' role and fetches the preferred name of the student.
    """
    # Ensure the user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this page."), frappe.PermissionError)

    # Check if the user has the 'Student' role
    user_roles = frappe.get_roles(frappe.session.user)
    if "Student" not in user_roles:
        frappe.throw(_("You are not authorized to access this page."), frappe.PermissionError)

    # Fetch the student document linked to the user
    student = frappe.get_value("Student", {"user_id": frappe.session.user}, "student_preferred_name")
    if not student:
        frappe.throw(_("Student profile not found. Please contact the administrator."))

    # Add the preferred name to the context
    context.student_preferred_name = student
    context.title = "Student Portal"
    return context
