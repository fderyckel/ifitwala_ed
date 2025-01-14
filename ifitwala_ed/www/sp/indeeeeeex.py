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

    # Step 1: Retrieve student image path
    student_image = frappe.db.get_value("Student", {"student_email": frappe.session.user}, "student_image")

    frappe.log_error(f"Retrieved student_image: {student_image}", title="Debug: Student Image Path")

    if not student_image:
        frappe.throw(_("No image found for this student."))

    try:
        # Step 2: Validate file existence in the File doctype
        file_doc = frappe.get_doc("File", {"file_url": student_image})
        if not file_doc:
            frappe.throw(_("File record not found for the given image."))

        frappe.log_error(f"File document found: {file_doc.file_name}", title="Debug: File Document")

        # Step 3: Fetch the file content
        file_content, file_name = get_file(student_image)

        frappe.log_error(f"File Content Retrieved: Length = {len(file_content)}", title="Debug: File Content")

        if not file_name or not isinstance(file_name, str):
            frappe.throw(_("Invalid file name. Please contact the administrator."))

        # Step 4: Determine MIME type
        content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        frappe.log_error(f"Determined Content Type: {content_type}", title="Debug: Content Type")

        # Step 5: Build and return the response
        response = Response(file_content, content_type=content_type)
        response.headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        return response

    except Exception as e:
        frappe.log_error(message=str(e), title="Error in get_student_image_file")
        frappe.throw(_("Unable to retrieve the image. Please contact the administrator."))