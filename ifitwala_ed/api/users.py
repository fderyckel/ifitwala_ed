# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

import frappe

from ifitwala_ed.routing.policy import (
    STAFF_PORTAL_ROLES,
    has_active_employee_profile,
    has_staff_portal_access,
    resolve_login_redirect_path,
)

# Backwards-compatible export used by existing modules/tests.
STAFF_ROLES = STAFF_PORTAL_ROLES


def _emit_login_redirect_trace(*, user: str, roles: set[str], path: str, stage: str) -> None:
    """Temporary diagnostics for login redirect debugging."""
    request = getattr(frappe, "request", None)
    request_path = str(getattr(request, "path", "") or "")
    cmd = str((getattr(frappe, "form_dict", frappe._dict()) or frappe._dict()).get("cmd") or "")

    payload = {
        "stage": stage,
        "user": user,
        "roles": sorted(roles),
        "resolved_path": path,
        "has_active_employee_profile": _has_active_employee_profile(user=user, roles=roles),
        "has_staff_portal_access": _has_staff_portal_access(user=user, roles=roles),
        "request_path": request_path,
        "cmd": cmd,
    }
    frappe.log_error(
        title="LOGIN REDIRECT TRACE",
        message=frappe.as_json(payload),
    )


def _set_login_redirect_state(*, path: str, login_manager=None) -> None:
    """
    Apply redirect state across all Frappe login response channels.

    This avoids reliance on exception-based redirects and keeps behavior stable
    across login handler phases (on_login + on_session_creation).
    """
    if hasattr(frappe, "form_dict"):
        frappe.form_dict["redirect_to"] = path
        frappe.form_dict["redirect-to"] = path

    if login_manager is not None:
        try:
            login_manager.home_page = path
        except Exception:
            pass

    local_login_manager = getattr(frappe.local, "login_manager", None)
    if local_login_manager is not None:
        try:
            local_login_manager.home_page = path
        except Exception:
            pass

    frappe.local.response["home_page"] = path
    frappe.local.response["redirect_to"] = path


def _self_heal_employee_user_link(*, user: str, roles: set[str]) -> None:
    """
    Backfill missing Employee.user_id links during login when there is exactly one
    Active Employee row matching the login email.
    """
    if "Employee" not in roles and not (roles & STAFF_PORTAL_ROLES):
        return
    if frappe.db.exists("Employee", {"user_id": user, "employment_status": "Active"}):
        return

    login_email = (frappe.db.get_value("User", user, "email") or user or "").strip()
    if not login_email:
        return

    matches = frappe.get_all(
        "Employee",
        filters={
            "employment_status": "Active",
            "employee_professional_email": login_email,
        },
        fields=["name", "user_id"],
        limit_page_length=2,
    )
    if len(matches) != 1:
        return

    current_user_id = str(matches[0].get("user_id") or "").strip()
    if current_user_id and current_user_id != user:
        return

    employee_name = matches[0]["name"]
    frappe.db.set_value("Employee", employee_name, "user_id", user, update_modified=False)

    try:
        from ifitwala_ed.hr.employee_access import sync_user_access_from_employee

        sync_user_access_from_employee(frappe.get_doc("Employee", employee_name))
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"Employee link self-heal sync failed for user {user} and employee {employee_name}",
        )


def _has_active_employee_profile(*, user: str, roles: set) -> bool:
    """Return True when user has an active Employee record."""
    return has_active_employee_profile(user=user, roles=roles)


def _has_staff_portal_access(*, user: str, roles: set) -> bool:
    """Return True when user should land on the staff portal."""
    return has_staff_portal_access(user=user, roles=roles)


def _resolve_login_redirect_path(*, user: str, roles: set) -> str:
    """
    Resolve the appropriate portal path based on user roles.

    Priority order (locked):
    1. Admissions Applicant -> /admissions
    2. Active Employee profile or staff role -> /portal/staff
    3. Student -> /portal/student
    4. Guardian -> /portal/guardian
    5. Fallback -> /portal/staff
    """
    return resolve_login_redirect_path(user=user, roles=roles)


def redirect_user_to_entry_portal(login_manager=None):
    """
    Login redirect handler: sets LoginManager.home_page only.

    Bound to both:
        - on_login
        - on_session_creation

    We rely exclusively on LoginManager.home_page so Desk login
    respects the redirect target instead of falling back to /app.
    """

    user = frappe.session.user
    if not user or user == "Guest":
        return

    roles = set(frappe.get_roles(user))

    # Heal link before resolving final roles
    _self_heal_employee_user_link(user=user, roles=roles)
    roles = set(frappe.get_roles(user))

    path = _resolve_login_redirect_path(user=user, roles=roles)

    # Diagnostic (optional — remove once stable)
    stage = "on_session_creation" if login_manager else "on_login"
    _emit_login_redirect_trace(user=user, roles=roles, path=path, stage=stage)

    # The only thing that matters for Desk login:
    if login_manager:
        login_manager.home_page = path


@frappe.whitelist()
def get_users_with_role(doctype, txt, searchfield, start, page_len, filters):
    """Return enabled users matching the provided role for link-field queries."""
    role = filters.get("role") if filters else None
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

    return frappe.db.sql(
        query,
        {
            "role": role,
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )
