# ifitwala_ed/admission/api/cockpit/access.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES

ALLOWED_COCKPIT_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", "Administrator"}
INVALID_SESSION_USERS = {"guest", "none", "null", "undefined"}


def _to_text(value) -> str:
    return str(value or "").strip()


def _get_roles_for_user(user: str) -> set[str]:
    try:
        return set(frappe.get_roles(user))
    except Exception as exc:
        message = _to_text(exc).lower()
        if "not found" in message and _to_text(user).lower() in INVALID_SESSION_USERS:
            frappe.throw(_("You need to sign in to access Admissions Cockpit."), frappe.PermissionError)
        raise


def _ensure_cockpit_access(user: str | None = None) -> str:
    resolved_user = _to_text(user or frappe.session.user)
    if not resolved_user or resolved_user.lower() in INVALID_SESSION_USERS:
        frappe.throw(_("You need to sign in to access Admissions Cockpit."), frappe.PermissionError)

    roles = _get_roles_for_user(resolved_user)
    if roles & ALLOWED_COCKPIT_ROLES:
        return resolved_user

    frappe.throw(_("You do not have permission to access Admissions Cockpit."), frappe.PermissionError)
    return resolved_user
