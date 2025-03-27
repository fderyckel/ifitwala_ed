# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import os
import random
import string
from frappe.utils import get_files_path
from frappe import _

def rename_and_move_student_image(student_docname, current_image_url):
  current_file_name = os.path.basename(current_image_url)

  # Check if already in correct format
  if (current_file_name.startswith(student_docname + "_") and
      len(current_file_name.split("_")[1].split(".")[0]) == 6):
    return current_image_url 

  file_extension = os.path.splitext(current_file_name)[1]
  random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
  expected_file_name = f"{student_docname}_{random_suffix}{file_extension}" 
  
  student_folder_fm_path = "Home/student"

  if not frappe.db.exists("File", {"file_name": "student", "folder": "Home"}): 
    student_folder = frappe.get_doc({
      "doctype": "File",
      "file_name": "student",
      "is_folder": 1,
      "folder": "Home"
    })
    student_folder.insert(ignore_permissions=True)

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
       _("No File doc found for {0}, attached_to=Student {1}").format(current_image_url, student_docname)
    )
    return

  file_doc = frappe.get_doc("File", file_name)

  old_file_path = os.path.join(get_files_path(), file_doc.file_name)
  new_file_path = os.path.join(get_files_path(), "student", expected_file_name)

  if os.path.exists(old_file_path):
    os.rename(old_file_path, new_file_path)
  else:
    frappe.log_error(_("Original file not found: {0}").format(old_file_path))
    return

  file_doc.file_name = expected_file_name
  file_doc.file_url = f"/files/student/{expected_file_name}"
  file_doc.folder = "Home/student"
  file_doc.is_private = 0
  file_doc.save(ignore_permissions=True)

  frappe.publish_realtime('student_image_updated', {
    'student': student_docname,
    'file_url': file_doc.file_url
  })

  return file_doc.file_url 
