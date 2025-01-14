import frappe
from frappe import _
from frappe.utils.file_manager import get_file
from frappe.utils.response import build_response
import mimetypes

def get_context(context):
    # ... (rest of your get_context function remains the same)
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

@frappe.whitelist(allow_guest=False)
def get_student_image_file():
    """Fetches the student's image file content securely."""
    frappe.log_error("Starting get_student_image_file function", "Debug: Student Image")

    if frappe.session.user == "Guest":
        frappe.log_error("User is a Guest", "Debug: Student Image")
        frappe.throw(_("You must be logged in to access this resource."), frappe.PermissionError)

    # Fetch the student document associated with the logged-in user
    student_image = frappe.db.get_value("Student", {"student_email": frappe.session.user}, "student_image")
    frappe.log_error(f"Student image value: {student_image}", "Debug: Student Image")

    if not student_image:
        frappe.log_error("No image found for this student", "Debug: Student Image")
        frappe.throw(_("No image found for this student."))

    try:
        # Get the file using frappe.utils.file_manager.get_file
        file_content, file_name = get_file(student_image)
        frappe.log_error(f"File name from get_file: {file_name}", "Debug: Student Image")

        # Get the file extension
        file_extension = file_name.split(".")[-1].lower()
        frappe.log_error(f"File Extension: {file_extension}", "Debug: Student Image")

        # Determine the content type based on the file extension
        if file_extension == "jpg" or file_extension == "jpeg":
            content_type = "image/jpeg"
        elif file_extension == "png":
            content_type = "image/png"
        elif file_extension == "gif":
            content_type = "image/gif"
        else:
            content_type = "application/octet-stream"
        frappe.log_error(f"Content Type: {content_type}", "Debug: Student Image")

        # Build the response
        response = build_response("binary")
        response.data = file_content
        response.headers["Content-Disposition"] = f"inline; filename={file_name}"
        response.headers["Content-Type"] = content_type
        frappe.log_error("Response built successfully", "Debug: Student Image")
        return response

    except Exception as e:
        frappe.log_error(f"Exception in get_student_image_file: {e}", "Debug: Student Image")
        frappe.throw(_("Unable to retrieve the image. Please contact the administrator."))