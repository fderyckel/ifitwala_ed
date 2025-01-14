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
def get_student_image_file(student_email=None):
    """Fetch the student's image file content securely."""
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this resource."), frappe.PermissionError)

    # Fetch the student document associated with the logged-in user
    student = frappe.get_doc("Student", {"student_email": frappe.session.user})
    if not student:
        frappe.throw(_("Student profile not found. Please contact the administrator."))

    # Check if the student has an image
    file_path = student.student_image
    if not file_path:
        frappe.throw(_("No image found for this student."))

    # Validate that the file exists
    file_doc = frappe.get_doc("File", {"file_url": file_path})
    if not file_doc:
        frappe.throw(_("File record not found."))

    # Verify if the user is authorized
    if frappe.session.user != student.student_email:
        frappe.throw(_("You are not authorized to access this file."))

    # Serve the file content
    #file_content = frappe.utils.file_manager.get_file(file_doc.file_url).get("file_content")
    #frappe.local.response.filename = file_doc.file_name
    #frappe.local.response.filecontent = file_content
    #frappe.local.response.type = "binary"  # Correct for inline display

    #return frappe.local.response
    return frappe.utils.response.download_private_file(file_path)

