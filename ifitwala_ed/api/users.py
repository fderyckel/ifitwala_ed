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
    2. Active Employee -> /portal/staff
    3. Student -> /portal/student
    4. Guardian -> /portal/guardian
    5. Fallback -> /portal/student
    """
    return resolve_login_redirect_path(user=user, roles=roles)


def redirect_user_to_entry_portal():
    """
    Login redirect handler: Routes users to role-appropriate portal entry point.

    Policy:
    - Admissions Applicants -> /admissions
    - Active Employees -> /portal/staff
    - Students -> /portal/student
    - Guardians -> /portal/guardian
    - Fallback -> /portal/student

    Login redirect is response-only (no User.home_page write in the login flow).
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return

    roles = set(frappe.get_roles(user))
    path = _resolve_login_redirect_path(user=user, roles=roles)
    frappe.local.response["home_page"] = path
    frappe.local.response["redirect_to"] = path


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
