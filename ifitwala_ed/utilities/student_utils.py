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
            # Get the file document associated with the student image
            file_doc = frappe.get_doc("File", {"file_url": doc.student_image, "attached_to_doctype": "Student", "attached_to_name": doc.name})

            # Get the student's ID
            student_id = doc.name

            # Construct the expected file name
            file_extension = os.path.splitext(file_doc.file_name)[1]  # Get extension from the actual file name
            expected_file_name = f"{student_id}{file_extension}"

            # Check if a file with the expected name already exists in the "student" folder (private)
            student_folder_fm_path = "Home/student"
            expected_file_path = os.path.join(student_folder_fm_path, expected_file_name)

            if frappe.db.exists("File", {"file_url": f"/private/files/{expected_file_path}", "is_private": 1}):
                frappe.log_error(f"Image with name {expected_file_name} already exists for student {student_id}. Skipping.")
                return  # Stop processing

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

            # Construct the new file name and path (private)
            new_file_name = f"{student_id}{file_extension}"
            new_file_path = os.path.join("student", new_file_name)
            new_file_url = f"/private/files/{new_file_path}"

            # Check if the file is already private
            if not file_doc.is_private:
                # Get the current full file path (might be public initially)
                current_file_full_path = file_doc.get_full_path()

                # Construct the new full file path (private)
                new_file_full_path = os.path.join(get_site_path(), "private", "files", new_file_path)

                # Rename and move the file to the private directory
                # This might fail if Frappe has already moved the file; we'll handle that
                try:
                    os.rename(current_file_full_path, new_file_full_path)
                except FileNotFoundError:
                    frappe.log_error(f"File not found during rename. Likely already moved by Frappe: {current_file_full_path}")
                    # Attempt to update the file document with the assumed new location
                    if os.path.exists(new_file_full_path):
                         file_doc.file_name = new_file_name
                         file_doc.file_url = new_file_url
                         file_doc.folder = student_folder_fm_path
                         file_doc.is_private = 1
                         file_doc.save()
                         doc.student_image = file_doc.file_url
                         return

            # Update file document (for both cases: moved or already private)
            file_doc.file_name = new_file_name
            file_doc.file_url = new_file_url
            file_doc.folder = student_folder_fm_path
            file_doc.is_private = 1
            file_doc.save()

            # Update student document
            doc.student_image = file_doc.file_url

        except Exception as e:
            # Shorten the error message for the Error Log title
            error_msg = f"Error handling image for {doc.name}: {type(e).__name__} - {e.args[0] if e.args else ''}"
            frappe.log_error(error_msg)
            frappe.msgprint(error_msg)
