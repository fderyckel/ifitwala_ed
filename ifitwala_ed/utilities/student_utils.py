# /utilities/student_utils.py
import frappe
import os
import random
import string
from frappe.utils import get_files_path

def rename_student_image(doc):
    # Check if a student image exists and if it has already been renamed
    if not doc.student_image:
        return  # No image uploaded, nothing to do

    # Get the current file URL and File document
    file_url = doc.student_image
    file_doc = frappe.get_doc("File", {"file_url": file_url})

    # Skip renaming if the image already resides in the "student" folder
    if "student/" in file_doc.file_url:
        return

    # Generate the new filename: Student ID + 6 random characters + extension
    file_extension = os.path.splitext(file_doc.file_name)[1]  # Get file extension
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    new_filename = f"{doc.name}_{random_suffix}{file_extension}"

    # Define the new file path
    student_folder_path = os.path.join(get_files_path(), "student")
    os.makedirs(student_folder_path, exist_ok=True)  # Ensure the folder exists
    new_file_path = os.path.join(student_folder_path, new_filename)

    # Move the file to the new location
    old_file_path = frappe.utils.get_files_path(file_doc.file_name)
    if os.path.exists(old_file_path):
        os.rename(old_file_path, new_file_path)
    else:
        frappe.throw(_("Original file not found: {0}").format(old_file_path))

    # Update the file URL and set to public
    new_file_url = f"/files/student/{new_filename}"
    file_doc.file_url = new_file_url
    file_doc.is_private = 0  # Set file to public
    file_doc.save()

    # Update the student record with the new file URL
    doc.student_image = new_file_url
    doc.db_update()

    frappe.msgprint(_("Image successfully renamed and moved to: {0}").format(new_file_url))