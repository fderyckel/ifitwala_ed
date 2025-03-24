# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from frappe import _

def get_data(): 
  return {
    "fieldname": "school",
    "transactions": [
      {
        "label": _("Academic"),
        "items": ["Academic Year", "Program Enrollment"]
      }, 
      {
        "label": _("Curriculum"),
        "items": ["Pogram", "Course"]
       }, 
      {
        "label": _("Schedule"),
        "items": ["Student Group"]
      }, 
      {
        "label": _("Admin"),
        "items": ["Employee"]
      }      
    ]
  }