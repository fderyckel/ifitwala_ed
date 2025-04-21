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


def set_default_workspace_based_on_roles(doc, method):
    if doc.user_type != "System User":
        return

    roles = [r.role for r in doc.roles]
    new_workspace = None

    if "Nurse" in roles:
        new_workspace = "Health"
    elif "Academic Admin" in roles:
        new_workspace = "Settings"

    if new_workspace:
        frappe.msgprint(
            f"This user’s default workspace will be set to <b>{new_workspace}</b>.",
            title="Default Workspace Updated",
            indicator="blue"
        )

        if doc.default_workspace != new_workspace:
            doc.default_workspace = new_workspace

            # Send notification to the user
            frappe.enqueue(send_workspace_notification, user=doc.name, workspace=new_workspace)

def send_workspace_notification(user, workspace):
    if not frappe.db.exists("User", user):
        return

    frappe.get_doc({
        "doctype": "Notification Log",
        "subject": f"Default Workspace Changed to {workspace}",
        "for_user": user,
        "type": "Alert",
        "email_content": f"Your default workspace has been updated to <b>{workspace}</b>. Please log out and log in again to see the change.",
    }).insert(ignore_permissions=True)
