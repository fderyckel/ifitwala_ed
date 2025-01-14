import frappe
from frappe import _
from frappe.utils.file_manager import get_file
import mimetypes
from werkzeug.wsgi import Response

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
    student_data = frappe.db.get_value(
        "Student",
        {"student_email": frappe.session.user},
        ["student_preferred_name", "student_image"],
        as_dict=True
    )

    if not student_data:
        frappe.throw(_("Student profile not found. Please contact the administrator."))

    # Add the preferred name and image to the context
    context.student_preferred_name = student_data.get("student_preferred_name", "Student")
    context.student_image = student_data.get("student_image", None)
    context.title = "Student Portal"
    return context



@frappe.whitelist()
def get_student_image_url():
    """Fetches the URL of the logged-in student's image securely."""
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this resource."), frappe.PermissionError)

    student = frappe.db.get_value(
        "Student",
        {"student_email": frappe.session.user},
        ["student_image"],
        as_dict=True,
    )

    if not student or not student.student_image:
        frappe.throw(_("No image found for this student."))

    return frappe.utils.file_manager.get_file_url(student.student_image)


@frappe.whitelist(allow_guest=False)
def get_student_image_file():
    """Fetch and serve the student's image securely."""
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this resource."), frappe.PermissionError)

    # Fetch the student's image path
    student_image = frappe.db.get_value("Student", {"student_email": frappe.session.user}, "student_image")

    if not student_image:
        frappe.throw(_("No image found for this student."))

    try:
        # Retrieve the file content and name
        file_content, file_name = get_file(student_image)

        # Guess the MIME type based on the file name
        content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        # Manually build the response
        response = Response(file_content)
        response.headers["Content-Type"] = content_type
        response.headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        return response

    except Exception as e:
        frappe.log_error(f"Error retrieving student image: {str(e)}", _("Student Image Retrieval Error"))
        frappe.throw(_("Unable to retrieve the image. Please contact the administrator."))

