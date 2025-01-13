# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from ifitwala_ed.utilities.student_portal_utils import get_student_data, get_student_logs
from frappe import _

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

    return context