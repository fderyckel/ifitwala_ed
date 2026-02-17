# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/hr/workspace_utils.py

import frappe

from ifitwala_ed.routing.policy import is_portal_home_page


def send_workspace_notification(user, workspace):
    if not frappe.db.exists("User", user):
        return
    frappe.get_doc(
        {
            "doctype": "Notification Log",
            "subject": f"Default Workspace Changed to {workspace}",
            "for_user": user,
            "type": "Alert",
            "email_content": f"Your default workspace has been updated to <b>{workspace}</b>. Please log out and log in again to see the change.",
        }
    ).insert(ignore_permissions=True)


def set_default_workspace_based_on_roles(doc, method):
    """
    Refactored to suggest workspace from Employee History + Designation defaults.
    Still runs on User.validate (per hooks) as a safety net.

    Portal-first rule:
    - If a user has a portal home_page (/student|/staff|/guardian or legacy /portal/*), do not touch Desk workspaces.
    """
    if doc.user_type != "System User":
        return

    home_page = (getattr(doc, "home_page", "") or "").strip()
    if is_portal_home_page(home_page):
        return

    # compute suggested workspace from effective access
    try:
        from ifitwala_ed.hr.employee_access import effective_workspace_for_user

        suggested_workspace = effective_workspace_for_user(doc.name)
    except Exception:
        suggested_workspace = None

    # validate current workspace existence
    def _exists_ws(ws: str | None) -> bool:
        return bool(ws) and frappe.db.exists("Workspace", ws)

    workspace_is_valid = _exists_ws(doc.default_workspace)

    # If default workspace points to a missing workspace, swap or clear it.
    if doc.default_workspace and not workspace_is_valid:
        if suggested_workspace and _exists_ws(suggested_workspace) and doc.default_workspace != suggested_workspace:
            doc.default_workspace = suggested_workspace
            frappe.msgprint(
                f"This user's default workspace referenced a missing workspace and has been changed to <b>{suggested_workspace}</b> based on effective access.",
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

    # No suggestion or roles didn’t imply a workspace
    if not suggested_workspace:
        return

    # If no default is set, use suggested.
    if not doc.default_workspace and _exists_ws(suggested_workspace):
        doc.default_workspace = suggested_workspace
        frappe.msgprint(
            f"This user's default workspace has been set to <b>{suggested_workspace}</b> based on effective access.",
            title="Default Workspace Updated",
            indicator="blue",
        )
        frappe.enqueue(send_workspace_notification, user=doc.name, workspace=suggested_workspace)
    # Else: keep user’s current choice; just inform (same as your previous behavior)
    elif doc.default_workspace != suggested_workspace:
        frappe.msgprint(
            f"This user already has a default workspace set to <b>{doc.default_workspace}</b>, "
            f"which is different from the suggested workspace <b>{suggested_workspace}</b> based on effective access. "
            "No automatic update applied.",
            title="Default Workspace Preserved",
            indicator="yellow",
        )
