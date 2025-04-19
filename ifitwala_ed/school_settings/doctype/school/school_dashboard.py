# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from frappe import _

def get_dashboard_data(doc):
    return {
        "fieldname": "school",
        "transactions": [
            {
                "label": _("Academic"),
                "items": [
                    {
                        "type": "doctype",
                        "name": "Program Enrollment",
                        "filters": {"status": 1}
                    },
                    "Academic Year",
                    "Term",
                    "School Calendar"
                ]
            },
            {
                "label": _("Curriculum"),
                "items": ["Program", "Course"]
            },
            {
                "label": _("Admin"),
                "items": ["Employee"]
            }
        ]
    }


