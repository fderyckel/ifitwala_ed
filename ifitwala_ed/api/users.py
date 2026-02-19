# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import frappe

from ifitwala_ed.routing.policy import (
    STAFF_PORTAL_ROLES,
    has_active_employee_profile,
    has_staff_portal_access,
    resolve_login_redirect_path,
)

# Backwards-compatible export used by existing modules/tests.
STAFF_ROLES = STAFF_PORTAL_ROLES


def _incoming_redirect_target() -> str:
    request = getattr(frappe, "request", None)
    args = getattr(request, "args", None) or {}
    from_args = args.get("redirect-to") or args.get("redirect_to")
    if from_args:
        return str(from_args).strip()

    form = getattr(frappe, "form_dict", frappe._dict()) or frappe._dict()
    from_form = form.get("redirect-to") or form.get("redirect_to")
    return str(from_form or "").strip()


def _strip_redirect_query(url: str) -> str:
    parts = urlsplit(url)
    kept = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in {"redirect-to", "redirect_to"}
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept, doseq=True), parts.fragment))


def sanitize_login_redirect_param() -> None:
    """
    Guard against sticky Desk redirects (?redirect-to=/app) on /login.

    Frappe's login frontend can prioritize this query parameter over backend
    home-page resolution. We strip only this one value to preserve explicit
    non-Desk redirects.
    """
    request = getattr(frappe, "request", None)
    if not request:
        return

    path = str(getattr(request, "path", "") or "").strip()
    method = str(getattr(request, "method", "") or "").upper()
    incoming = _incoming_redirect_target()

    # Only neutralize sticky Desk redirects.
    if incoming != "/app":
        return

    # Always clear request-side redirect hints so downstream handlers don't reuse them.
    if hasattr(frappe, "form_dict"):
        frappe.form_dict["redirect_to"] = ""
        frappe.form_dict["redirect-to"] = ""

    # For login page GET requests, redirect to the same URL without redirect-to.
    if path == "/login" and method == "GET":
        full_path = str(getattr(request, "full_path", "") or "").strip()
        target = _strip_redirect_query(full_path or "/login")
        if target in {"/login?", "login?"}:
            target = "/login"
        frappe.log_error(
            title="LOGIN REDIRECT SANITIZED",
            message=frappe.as_json(
                {
                    "path": path,
                    "method": method,
                    "incoming_redirect_to": incoming,
                    "redirect_to": target,
                }
            ),
        )
        frappe.local.flags.redirect_location = target
        raise frappe.Redirect


def _user_has_home_page_field() -> bool:
    """Return True when User.home_page exists on this site schema."""
    try:
        return bool(frappe.get_meta("User").has_field("home_page"))
    except Exception:
        return False


def _get_user_home_page_safe(user: str) -> str | None:
    """Best-effort read for User.home_page that never breaks auth flow."""
    if not _user_has_home_page_field():
        return None
    try:
        return frappe.db.get_value("User", user, "home_page")
    except Exception as exc:
        if hasattr(frappe.db, "is_missing_column") and frappe.db.is_missing_column(exc):
            return None
        return None


def _set_user_home_page_safe(*, user: str, path: str) -> None:
    """Best-effort write for User.home_page that never breaks auth flow."""
    if not _user_has_home_page_field():
        return
    try:
        frappe.db.set_value("User", user, "home_page", path, update_modified=False)
    except Exception as exc:
        if hasattr(frappe.db, "is_missing_column") and frappe.db.is_missing_column(exc):
            return
        return


def _normalize_invalid_user_home_page(*, user: str, path: str) -> None:
    """
    Repair invalid User.home_page values that are not absolute paths.

    Canonical routes are absolute (start with '/'). Any non-empty relative value
    can produce broken login redirects and is normalized to the resolved path.
    """
    current_raw = _get_user_home_page_safe(user)
    current = str(current_raw or "").strip()
    if not current:
        return
    if current.startswith("/"):
        return
    target = path
    if target != current:
        _set_user_home_page_safe(user=user, path=target)


def _emit_login_redirect_trace(*, user: str, roles: set[str], path: str, stage: str) -> None:
    """Temporary diagnostics for login redirect debugging."""
    request = getattr(frappe, "request", None)
    request_path = str(getattr(request, "path", "") or "")
    cmd = str((getattr(frappe, "form_dict", frappe._dict()) or frappe._dict()).get("cmd") or "")

    user_home_page = _get_user_home_page_safe(user)

    payload = {
        "stage": stage,
        "user": user,
        "roles": sorted(roles),
        "resolved_path": path,
        "has_active_employee_profile": _has_active_employee_profile(user=user, roles=roles),
        "has_staff_portal_access": _has_staff_portal_access(user=user, roles=roles),
        "request_path": request_path,
        "cmd": cmd,
        "incoming_redirect_to": _incoming_redirect_target(),
        "user_home_page": user_home_page,
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
    if not hasattr(frappe.local, "response") or frappe.local.response is None:
        frappe.local.response = frappe._dict()

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
    Login redirect handler: Routes users to role-appropriate portal entry point.

    Policy:
    - Admissions Applicants -> /admissions
    - Active employees and staff-role users -> /portal/staff
    - Students -> /portal/student
    - Guardians -> /portal/guardian
    - Fallback -> /portal/staff

    Login redirect is response-only (no broad User.home_page writes in login flow).
    The same handler is bound to both on_login and on_session_creation so the
    target survives downstream Desk home-page resolution.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return

    roles = set(frappe.get_roles(user))
    _self_heal_employee_user_link(user=user, roles=roles)
    roles = set(frappe.get_roles(user))
    path = _resolve_login_redirect_path(user=user, roles=roles)

    # Self-heal malformed runtime values that can hijack login redirects.
    _normalize_invalid_user_home_page(user=user, path=path)

    stage = "on_session_creation" if login_manager is not None else "on_login"
    _emit_login_redirect_trace(user=user, roles=roles, path=path, stage=stage)

    # Force canonical portal target even when login was initiated with /app.
    _set_login_redirect_state(path=path, login_manager=login_manager)


def get_website_user_home_page(user=None) -> str:
    """
    Canonical website home-page resolver used by Frappe /login flows.

    This prevents stale site defaults from sending users to non-canonical routes.
    """
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "/login"

    roles = set(frappe.get_roles(user))
    _self_heal_employee_user_link(user=user, roles=roles)
    roles = set(frappe.get_roles(user))
    return _resolve_login_redirect_path(user=user, roles=roles)


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
