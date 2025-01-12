# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_url_to_form

def get_student_data():
    """Retrieves student data for the logged-in user."""
    user = frappe.session.user
    student_name = frappe.db.get_value("Student", {"student_email": user}, "name")

    if not student_name:
        return None

    student = frappe.get_doc("Student", student_name)
    return {
        "student": student,
        "student_url": get_url_to_form("Student", student.name)
    }

def get_student_logs():
    """Retrieves Student Logs visible to the logged-in student."""
    user = frappe.session.user
    student = frappe.db.get_value("Student", {"student_email": user}, "name")

    if not student:
        return []

    logs = frappe.get_all("Student Log",
        filters={
            "student": student,
            "visible_to_student": 1  # Filter for visible logs
        },
        fields=["date", "log_type", "log" , "author_name", "program", "visible_to_guardians"],
        order_by="date desc"
    )
    return logs

@frappe.whitelist()
def get_context(context):
    """Provides context for the student portal."""
    if "Student" not in frappe.get_roles():
        # Prevent unauthorized access
        frappe.throw(
            _("You do not have permission to access this page."),
            frappe.PermissionError
        )

    context.update(get_student_data())
    context["logs"] = get_student_logs()
    context["no_cache"] = 1