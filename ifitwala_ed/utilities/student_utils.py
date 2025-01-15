import frappe
import os
import random
import string
from frappe.utils import get_files_path
from frappe import _

def rename_student_image(doc, method):
  """
  Handles student image after Student document update:
  - Renames the image to the student's ID + 6 random characters + extension.
  - Moves the image to the "student" folder in the public file manager.
  - Skips processing if an image with the same name already exists.
  """
  if doc.student_image:
    try:
      # Get the student's ID
      student_id = doc.name 

      # Extract the current file name from the URL
      current_file_name = os.path.basename(doc.student_image)

      # Check if the image already follows the correct naming convention
      if current_file_name.startswith(student_id + "_") and \
         len(current_file_name.split("_")[1].split(".")[0]) == 6 and \
         current_file_name.split(".")[1].lower() in ["jpg", "jpeg", "png", "gif"]:
        return  # No need to throw an error, just exit

      # Construct the expected file name
      file_extension = os.path.splitext(doc.student_image)[1]
      random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
      expected_file_name = f"{student_id}_{random_suffix}{file_extension}"  # Include random suffix

      # Check if a file with the expected name already exists in the "student" folder
      student_folder_fm_path = "Home/student"
      expected_file_path = os.path.join(student_folder_fm_path, expected_file_name)
      # Check in public files
      if frappe.db.exists("File", {"file_url": f"/files/{expected_file_path}"}):  
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
      new_file_name = expected_file_name  # Use the expected file name with random suffix
      new_file_path = os.path.join(get_files_path(), "student", new_file_name)  # Get the full path

      # Rename the file first
      old_file_path = frappe.utils.get_files_path(file_doc.file_name)  # Get the current file path
      if os.path.exists(old_file_path):
        os.rename(old_file_path, new_file_path)  # Rename using os.rename
        file_doc.file_name = new_file_name  # Update the file_name in the File document
        file_doc.file_url = f"/files/student/{new_file_name}"  # Update the file_url
        file_doc.folder = "Home/student"
        file_doc.is_private = 0  # Set the file to public
        file_doc.save()
      else:
        frappe.throw(_("Original file not found: {0}").format(old_file_path))

      # Update student document
      doc.student_image = file_doc.file_url
      doc.db_update()

      frappe.msgprint(f"Image for student {student_id} has been renamed and moved to /files/student/{new_file_name}")

    except Exception as e:
      frappe.log_error(f"Error handling student image for {doc.name}: {e}")
      frappe.msgprint(f"Error handling student image for {doc.name}: {e}")