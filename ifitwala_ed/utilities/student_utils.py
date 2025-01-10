# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import os
from frappe.utils import get_site_path

def handle_student_image(doc, method):
    """
    Handles student image after Student document update:
    - Renames the image to the student's ID.
    - Moves the image to the "student" folder in the file manager.
    - Skips processing if an image with the same name already exists.
    """
    frappe.log_error("handle_student_image called - on_update")

    if doc.student_image:
        try:
            # Get the student's ID
            student_id = doc.name

            # Construct the expected file name
            file_extension = os.path.splitext(doc.student_image)[1]  # Get extension from the uploaded image URL
            expected_file_name = f"{student_id}{file_extension}"

            # Check if a file with the expected name already exists in the "student" folder
            student_folder_fm_path = "Home/student"
            expected_file_path = os.path.join(student_folder_fm_path, expected_file_name)
            if frappe.db.exists("File", {"file_url": f"/private/files/{expected_file_path}", "is_private": 1}):
                frappe.log_error(f"Image with name {expected_file_name} already exists for student {student_id}. Skipping.")
                return  # Stop processing

            # If the image doesn't exist, proceed with renaming and moving
            file_doc = frappe.get_doc("File", {"file_url": doc.student_image, "attached_to_doctype": "Student", "attached_to_name": doc.name})

            # Create the "student" folder if it doesn't exist (in the private files directory)
            student_folder_path = os.path.join(get_site_path(), "private", "files", "student")
            if not os.path.exists(student_folder_path):
                os.makedirs(student_folder_path)
                # Also create the folder in the File Manager
                if not frappe.db.exists("File", {"file_name": "student", "folder": "Home"}):
                    student_folder = frappe.get_doc({
                        "doctype": "File",
                        "file_name": "student",
                        "is_folder": 1,
                        "folder": "Home"
                    })
                    student_folder.insert()

            # Construct the new file name and path
            new_file_name = f"{student_id}{file_extension}"
            new_file_path = os.path.join("student", new_file_name)

            # Get the current full file path
            current_file_full_path = file_doc.get_full_path()

            # Rename and move the file
            new_file_full_path = os.path.join(get_site_path(), "private", "files", new_file_path)
            os.rename(current_file_full_path, new_file_full_path)

            # Update file document and student document
            file_doc.file_name = new_file_name
            file_doc.file_url = f"/private/files/{new_file_path}"
            file_doc.folder = student_folder_fm_path
            file_doc.is_private = 1
            file_doc.save()

            doc.student_image = file_doc.file_url
            # doc.save() # No need to save the doc again

        except Exception as e:
            frappe.log_error(f"Error handling student image for {doc.name}: {e}")
            frappe.msgprint(f"Error handling student image for {doc.name}: {e}")