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

    # Check if roles have changed
    previous_doc = doc.get_doc_before_save()
    if previous_doc:
        old_roles = set(r.role for r in previous_doc.roles)
        new_roles = set(r.role for r in doc.roles)

        if old_roles == new_roles:
            # No role change → no action needed
            return

    # Determine appropriate workspace based on roles
    roles = [r.role for r in doc.roles]
    new_workspace = None

    if "Nurse" in roles:
        new_workspace = "Health"
    elif "Academic Admin" in roles:
        new_workspace = "Settings"

    if not new_workspace:
        # No relevant role → no need to adjust workspace
        return

    # Now decide what to do depending on current default_workspace
    if not doc.default_workspace:
        # No default_workspace set → we set it
        doc.default_workspace = new_workspace
        frappe.msgprint(
            f"This user’s default workspace has been set to <b>{new_workspace}</b> based on their role.",
            title="Default Workspace Updated",
            indicator="blue"
        )
        frappe.enqueue(send_workspace_notification, user=doc.name, workspace=new_workspace)
    elif doc.default_workspace != new_workspace:
        # There is already a workspace set, but it does not match the role → inform
        frappe.msgprint(
            f"This user already has a default workspace set to <b>{doc.default_workspace}</b>, "
            f"which is different from the suggested workspace <b>{new_workspace}</b> based on their role. "
            f"No automatic update applied.",
            title="Default Workspace Preserved",
            indicator="yellow"
        )
    else:
        # Workspace already matches the role → silent
        pass



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
