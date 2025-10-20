# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/hr/workspace_utils.py

import frappe

def set_default_workspace_based_on_roles(doc, method):
    # Observe role changes plus any lingering workspace that no longer exists
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
        ("Counselor", "Counselors"),
        ("Instructor", "Academics"),
    )

    def suggest_workspace() -> str | None:
        for role, workspace in role_workspace_priority:
            if role in current_roles and frappe.db.exists("Workspace", workspace):
                return workspace
        return None

    suggested_workspace = suggest_workspace()
    workspace_is_valid = True
    if doc.default_workspace:
        workspace_is_valid = frappe.db.exists("Workspace", doc.default_workspace)

    if doc.default_workspace and not workspace_is_valid:
        if doc.user_type == "System User" and suggested_workspace and doc.default_workspace != suggested_workspace:
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

    if doc.user_type != "System User":
        return

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

