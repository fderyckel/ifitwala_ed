# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# In your_app_name/your_module/student.py

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

            # Create the "student" folder if it doesn't exist
            student_folder_path = os.path.join(get_site_path(), "public", "files", "student")
            if not os.path.exists(student_folder_path):
                os.makedirs(student_folder_path)

            # Construct the new file name and path
            file_extension = os.path.splitext(file_doc.file_name)[1]
            new_file_name = f"{student_id}{file_extension}"
            new_file_path = os.path.join("student", new_file_name)  # Relative path for the file manager

            # Get the current full file path
            current_file_full_path = os.path.join(get_site_path(), "public", "files", file_doc.file_name)

            # Rename and move the file
            new_file_full_path = os.path.join(get_site_path(), "public", "files", new_file_path)
            os.rename(current_file_full_path, new_file_full_path)


            # Update file document and student document
            file_doc.file_name = new_file_name
            file_doc.file_url = f"/files/{new_file_path}"
            file_doc.folder = "student"  # Assuming a File doctype folder named "student" exists
            file_doc.is_private = 0 # Set to public, 1 for private. Private is going to be in the private folder.
            file_doc.save()

            doc.student_image = file_doc.file_url
            doc.save()

        except Exception as e:
            frappe.log_error(f"Error handling student image for {doc.name}: {e}")
            # Optionally: frappe.throw("An error occurred while processing the image.")