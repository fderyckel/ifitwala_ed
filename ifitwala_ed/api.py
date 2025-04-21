# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe

def redirect_student_to_portal():
    user = frappe.session.user
    roles = frappe.get_roles(user)

    # Only proceed if the user has the Student role
    if "Student" in roles:
        # Check that the user has a linked Student record
        if frappe.db.exists("Student", {"student_user_id": user}):
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = "/sp"
        else:
            # Optional: log for debugging, but don't interrupt login flow
            frappe.logger().warning(f"Student role but no Student profile found for user: {user}")

    # 🏥 Redirect Nurses to Health Workspace (Desk app)
    elif "Nurse" in roles:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/health"

    # 🏥 Redirect Nurses to Health Workspace (Desk app)
    elif "Academic Admin" in roles:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/app/settings"             