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

    # We care both about role changes and about stale workspace references
    current_roles = {r.role for r in doc.roles}
    previous_doc = doc.get_doc_before_save()
    roles_changed = True
    if previous_doc:
        previous_roles = {r.role for r in previous_doc.roles}
        roles_changed = previous_roles != current_roles

    role_workspace_priority = (
        ("Nurse", "Health"),
        ("Academic Admin", "Admin"),
        ("Curriculum Coordinator", "Curriculum"),
        ("Counselor", "Counsel"),
        ("Instructor", "Academics"),
    )

    suggested_workspace = None
    for role, workspace in role_workspace_priority:
        if role in current_roles and frappe.db.exists("Workspace", workspace):
            suggested_workspace = workspace
            break

    current_workspace_exists = True
    if doc.default_workspace:
        current_workspace_exists = frappe.db.exists("Workspace", doc.default_workspace)

    if doc.default_workspace and not current_workspace_exists:
        if suggested_workspace and doc.default_workspace != suggested_workspace:
            doc.default_workspace = suggested_workspace
            frappe.msgprint(
                f"This user's default workspace referenced a missing workspace and has been changed to <b>{suggested_workspace}</b> based on their role.",
                title="Default Workspace Updated",
                indicator="blue",
            )
            frappe.enqueue(send_workspace_notification, user=doc.name, workspace=suggested_workspace)
        else:
            doc.default_workspace = None
            frappe.msgprint(
                "This user's default workspace referenced a workspace that no longer exists and has been cleared.",
                title="Default Workspace Cleared",
                indicator="orange",
            )
        return

    # No relevant role or no changes → nothing further to do
    if not suggested_workspace or not roles_changed:
        return

    if not doc.default_workspace:
        doc.default_workspace = suggested_workspace
        frappe.msgprint(
            f"This user's default workspace has been set to <b>{suggested_workspace}</b> based on their role.",
            title="Default Workspace Updated",
            indicator="blue",
        )
        frappe.enqueue(send_workspace_notification, user=doc.name, workspace=suggested_workspace)
    elif doc.default_workspace != suggested_workspace:
        frappe.msgprint(
            f"This user already has a default workspace set to <b>{doc.default_workspace}</b>, "
            f"which is different from the suggested workspace <b>{suggested_workspace}</b> based on their role. "
            "No automatic update applied.",
            title="Default Workspace Preserved",
            indicator="yellow",
        )

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

@frappe.whitelist()
def get_users_with_role(doctype, txt, searchfield, start, page_len, filters):
	role = filters.get("role")
	if not role:
		return []

	query = """
		SELECT u.name, u.full_name
		FROM `tabUser` u
		JOIN `tabHas Role` r ON u.name = r.parent
		WHERE r.role = %(role)s
			AND u.enabled = 1
			AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.name
		LIMIT %(start)s, %(page_len)s
	"""

	return frappe.db.sql(query, {
		"role": role,
		"txt": f"%{txt}%",
		"start": start,
		"page_len": page_len
	})


