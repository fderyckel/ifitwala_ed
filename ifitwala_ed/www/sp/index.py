import frappe
from frappe import _
from frappe.utils.file_manager import get_file
import mimetypes
from werkzeug.wrappers import Response

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
    """Fetches the student's image file content securely."""
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this resource."), frappe.PermissionError)

    # Step 1: Get the student image file path
    student_image = frappe.db.get_value("Student", {"student_email": frappe.session.user}, "student_image")
    if not student_image:
        frappe.throw(_("No image found for this student."))

    # Debug log for `student_image`
    frappe.log_error(message=f"Student image path: {student_image}", title="Debug: Student Image Retrieval")

    try:
        # Step 2: Fetch file content and metadata
        file_content, file_name = get_file(student_image)

        # Validate `file_name`
        if not file_name or not isinstance(file_name, str):
            frappe.log_error(message=f"Invalid file metadata. student_image: {student_image}, file_name: {file_name}",
                             title="Debug: Invalid File Metadata")
            frappe.throw(_("Invalid file name. Please contact the administrator."))

        # Step 3: Determine MIME type
        content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        # Debug log for MIME type and file_name
        frappe.log_error(message=f"Content-Type: {content_type}, File Name: {file_name}", title="Debug: File Metadata")

        # Step 4: Build the response
        response = Response(file_content, content_type=content_type)
        response.headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        return response

    except Exception as e:
        frappe.log_error(message=str(e), title="Error in get_student_image_file")
        frappe.throw(_("Unable to retrieve the image. Please contact the administrator."))