# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from frappe import _

def get_data(): 
  return {
    "fieldname": "student",
    "transactions": [
      {
        "label": _("Academic"),
        "items": ["Program Enrollment", "Course Enrollment", "Student Group"]
      }, 
      {
        "label": _("Communication"),
        "items": ["Student Log", "Contact"]
       }, 
      {
        "label": _("Health"),
        "items": ["Student Patient"]
      }
    ]
  }