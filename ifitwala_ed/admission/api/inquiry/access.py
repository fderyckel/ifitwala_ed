# ifitwala_ed/admission/api/inquiry/access.py

from __future__ import annotations

import frappe
from frappe import _

ALLOWED_ANALYTICS_ROLES = {
    "Academic Admin",
    "Admission Officer",
    "Admission Manager",
    "System Manager",
    "Administrator",
}


def _ensure_access(user: str | None = None) -> str:
    """Gate analytics to authorized staff roles."""
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access Inquiry Analytics."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & ALLOWED_ANALYTICS_ROLES:
        return user

    frappe.throw(_("You do not have permission to access Inquiry Analytics."), frappe.PermissionError)
    return user
