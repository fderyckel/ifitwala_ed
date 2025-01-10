# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import os
from frappe.utils import get_site_path

def handle_student_image(doc, method):
    """
    Handles student image after Student document save:
    - Renames the image to the student's ID.
    - Moves the image to the "student" folder in the file manager.
    """
    if doc.student_image:
        try:
            file_doc = frappe.get_doc("File", {"file_url": doc.student_image, "attached_to_doctype": "Student", "attached_to_name": doc.name})

            # Get the student's ID
            student_id = doc.name

            # Create the "student" folder if it doesn't exist (in the private files directory)
            student_folder_fm_path = "Home/student"  # Path in the File Manager
            student_folder_path = os.path.join(get_site_path(), "private", "files", "student") # Path in the Private files directory

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
            file_extension = os.path.splitext(file_doc.file_name)[1]
            new_file_name = f"{student_id}{file_extension}"
            new_file_path = os.path.join("student", new_file_name)

            # Get the current full file path (should now be in the private files directory)
            current_file_full_path = file_doc.get_full_path()

            # Rename and move the file (within the private files directory)
            new_file_full_path = os.path.join(get_site_path(), "private", "files", new_file_path)
            os.rename(current_file_full_path, new_file_full_path)

            # Update file document and student document
            file_doc.file_name = new_file_name
            file_doc.file_url = f"/private/files/{new_file_path}" # Update file_url to be under private
            file_doc.folder = student_folder_fm_path
            file_doc.is_private = 1  # Keep the file private
            file_doc.save()

            doc.student_image = file_doc.file_url
            doc.save()

        except Exception as e:
            frappe.log_error(f"Error handling student image for {doc.name}: {e}")
            frappe.msgprint(f"Error handling student image for {doc.name}: {e}")