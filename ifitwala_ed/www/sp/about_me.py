import frappe
from frappe import _

def get_context(context):
    """
    Prepares the context for the 'About Me' page.
    Fetches student details linked to the logged-in user.
    """
    # Ensure the user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this page."), frappe.PermissionError)

    # Fetch the student record
    student = frappe.get_doc("Student", {"student_email": frappe.session.user})
    if not student:
        frappe.throw(_("Student profile not found. Please contact the administrator."))

    # Add student details to the context
    context.student_image = student.student_image
    context.student_first_name = student.student_first_name
    context.student_middle_name = student.student_middle_name
    context.student_last_name = student.student_last_name
    context.student_email = student.student_email
    context.student_mobile_number = student.student_mobile_number
    context.student_dob = student.student_date_of_birth
    context.student_gender = student.student_gender
    context.student_first_language = student.student_first_language
    context.student_second_language = student.student_second_language or None
    context.title = "About Me"
    return context
