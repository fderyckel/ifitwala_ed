# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import os
import random
import string
from frappe.utils import get_files_path
from frappe import _

def rename_student_uploaded_image(doc, method):
    if doc.attached_to_doctype != "Student":
        return  # Clearly exit early if not attached to a Student doc

    student_docname = doc.attached_to_name
    current_file_name = doc.file_name

    # Clearly avoid double renaming
    if current_file_name.startswith(student_docname + "_") and len(current_file_name.split("_")[1].split(".")[0]) == 6:
        return

    # Clearly generate new filename
    file_extension = os.path.splitext(doc.file_name)[1]
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    expected_file_name = f"{student_docname}_{random_suffix}{file_extension}"

    # Ensure "student" folder clearly exists
    if not frappe.db.exists("File", {"file_name": "student", "folder": "Home"}):
        student_folder = frappe.get_doc({
            "doctype": "File",
            "file_name": "student",
            "is_folder": 1,
            "folder": "Home"
        })
        student_folder.insert(ignore_permissions=True)

    old_file_path = os.path.join(get_files_path(), doc.file_name)
    new_file_path = os.path.join(get_files_path(), "student", expected_file_name)

    if os.path.exists(old_file_path):
        os.rename(old_file_path, new_file_path)
    else:
        frappe.log_error(_("Original file not found: {0}").format(old_file_path))
        return

    # Update File doc explicitly (robust!)
    doc.file_name = expected_file_name
    doc.file_url = f"/files/student/{expected_file_name}"
    doc.folder = "Home/student"
    doc.is_private = 0
    doc.save(ignore_permissions=True)

    # Clearly update Student field safely (but no timestamp issues, as it’s in the same transaction as File insertion)
    frappe.db.set_value(
        "Student",
        student_docname,
        "student_image",
        doc.file_url,
        update_modified=False
    )



