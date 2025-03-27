# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import os
import random
import string
from frappe.utils import get_files_path
from frappe import _

def rename_and_move_student_image(student_docname, current_image_url):
    student = frappe.get_doc("Student", student_docname)
    current_file_name = os.path.basename(current_image_url)

    # Check if already renamed
    if (
        current_file_name.startswith(student_docname + "_")
        and len(current_file_name.split("_")[1].split(".")[0]) == 6
        and current_file_name.split(".")[1].lower() in ["jpg", "jpeg", "png", "gif"]
    ):
        return

    file_extension = os.path.splitext(current_file_name)[1]
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    expected_file_name = f"{student_docname}_{random_suffix}{file_extension}"

    student_folder_fm_path = "Home/student"
    expected_file_path = os.path.join(student_folder_fm_path, expected_file_name)

    # Ensure "student" folder exists
    if not frappe.db.exists("File", {"file_name": "student", "folder": "Home"}):
        student_folder = frappe.get_doc({
            "doctype": "File",
            "file_name": "student",
            "is_folder": 1,
            "folder": "Home"
        })
        student_folder.insert(ignore_permissions=True)

    # Original file doc
    file_name = frappe.db.get_value("File",
        {
            "file_url": current_image_url,
            "attached_to_doctype": "Student",
            "attached_to_name": student_docname
        },
        "name"
    )

    if not file_name:
        frappe.log_error(
            title=_("Missing File Doc"),
            message=_("No File doc found for {0}, attached_to=Student {1}").format(current_image_url, student_docname)
        )
        return

    file_doc = frappe.get_doc("File", file_name)

    old_file_path = os.path.join(get_files_path(), file_doc.file_name)
    new_file_path = os.path.join(get_files_path(), "student", expected_file_name)

    try:
        if os.path.exists(old_file_path):
            os.rename(old_file_path, new_file_path)
        else:
            frappe.throw(_("Original file not found: {0}").format(old_file_path))

        file_doc.file_name = expected_file_name
        file_doc.file_url = f"/files/student/{expected_file_name}"
        file_doc.folder = "Home/student"
        file_doc.is_private = 0
        file_doc.save(ignore_permissions=True)

        # Update student_image in Student doc safely via db.set_value
        frappe.db.set_value("Student", student_docname, "pending_student_image",
            file_doc.file_url,
            update_modified=False  # Prevents changing modified timestamp
        )

        frappe.publish_realtime('student_image_updated', {'student': student_docname})

    except Exception as e:
        frappe.log_error(
            title=_("Student Image Rename Error"),
            message=f"Error renaming student image for {student_docname}: {e}"
        )
