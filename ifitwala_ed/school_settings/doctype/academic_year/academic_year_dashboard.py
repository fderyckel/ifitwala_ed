# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from frappe import _

def get_data(): 
  return {
    "fieldname": "academic_year",
    "transactions": [
      {
        "label": _("Academic"),
        "items": ["Academic Year", "Term", "School Calendar", "Student Log"]
      }, 
      {
        "label": _("Schedule"),
        "items": ["Program Enrollment", "Student Group"]
       }     
    ]
  }