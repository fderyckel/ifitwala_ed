# /utilities/student_utils.py
import frappe
import os
import random
import string
from frappe.utils import get_files_path

def rename_student_image(doc,method):  # Accept additional arguments
  """
  Handles student image after Student document update:
  - Renames the image to the student's ID.
  - Moves the image to the "student" folder in the file manager.
  - Skips processing if an image with the same name already exists.
  """
  if doc.student_image:
    try:
      # Get the student's ID
      student_id = doc.name

      # Construct the expected file name
      file_extension = os.path.splitext(doc.student_image)[1]
      expected_file_name = f"{student_id}{file_extension}"

      # Check if a file with the expected name already exists in the "student" folder
      student_folder_fm_path = "Home/student"
      expected_file_path = os.path.join(student_folder_fm_path, expected_file_name)
      if frappe.db.exists("File", {"file_url": f"/private/files/{expected_file_path}"}):
        frappe.log_error(f"Image with name {expected_file_name} already exists for student {student_id}. Skipping.")
        return

      # If the image doesn't exist, proceed with renaming and moving
      file_doc = frappe.get_doc("File", {"file_url": doc.student_image, "attached_to_doctype": "Student", "attached_to_name": doc.name})

      # Create the "student" folder if it doesn't exist
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

      # Rename and move the file using Frappe's File API
      file_doc.rename(new_file_name)
      file_doc.move(student_folder_fm_path)

      # Update file document
      file_doc.file_url = f"/private/files/{new_file_path}"  # Update file_url after moving
      file_doc.save()

      # Update student document
      doc.student_image = file_doc.file_url
      doc.db_update()

    except Exception as e:
      frappe.log_error(f"Error handling student image for {doc.name}: {e}")
      frappe.msgprint(f"Error handling student image for {doc.name}: {e}")

