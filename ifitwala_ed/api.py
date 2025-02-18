# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe

def redirect_student_to_portal():
    # Check if the logged-in user has the "Student" role
    if "Student" in frappe.get_roles(frappe.session.user):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/sp"