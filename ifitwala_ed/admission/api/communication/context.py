from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime

from ifitwala_ed.admission.api.communication.constants import (
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
    ALLOWED_STAFF_ROLES,
    INVALID_SESSION_USERS,
    SUPPORTED_CONTEXT_DOCTYPES,
)
from ifitwala_ed.admission.api.portal.access import _ensure_applicant_match


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _session_user() -> str:
    user = _to_text(getattr(frappe.session, "user", None))
    if not user:
        return ""
    if user.lower() in INVALID_SESSION_USERS:
        return ""
    return user


def _normalize_context(context_doctype: str | None, context_name: str | None) -> tuple[str, str]:
    doctype = _to_text(context_doctype)
    name = _to_text(context_name)
    if doctype not in SUPPORTED_CONTEXT_DOCTYPES:
        frappe.throw(
            _("Unsupported admissions communication context: {doctype}.").format(doctype=doctype or _("(empty)"))
        )
    if not name:
        frappe.throw(_("context_name is required."))
    return doctype, name


def _safe_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return get_datetime(value)
    except Exception:
        return None


def _resolve_student_applicant_row(applicant_name: str) -> dict:
    row = frappe.db.get_value(
        "Student Applicant",
        applicant_name,
        ["name", "organization", "school", "applicant_user"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Student Applicant {applicant} was not found.").format(applicant=applicant_name))
    return {
        "name": _to_text(row.get("name")),
        "organization": _to_text(row.get("organization")),
        "school": _to_text(row.get("school")),
        "applicant_user": _to_text(row.get("applicant_user")),
    }


def _require_actor_context(*, context_doctype: str, context_name: str) -> dict:
    user = _session_user()
    if not user:
        frappe.throw(_("You need to sign in to access admissions communications."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    context_row: dict
    applicant_user = ""

    if context_doctype == "Student Applicant":
        context_row = _resolve_student_applicant_row(context_name)
        applicant_user = _to_text(context_row.get("applicant_user"))
    else:
        frappe.throw(_("Unsupported admissions communication context: {doctype}.").format(doctype=context_doctype))

    if ADMISSIONS_APPLICANT_ROLE in roles:
        if context_doctype != "Student Applicant":
            frappe.throw(
                _("Applicant portal users can only access Student Applicant communication."), frappe.PermissionError
            )
        _ensure_applicant_match(context_name, user)
        return {
            "user": user,
            "roles": roles,
            "actor": "applicant",
            "context": context_row,
            "applicant_user": applicant_user,
            "portal_actor_user": user,
        }

    if ADMISSIONS_FAMILY_ROLE in roles:
        if context_doctype != "Student Applicant":
            frappe.throw(
                _("Applicant portal users can only access Student Applicant communication."), frappe.PermissionError
            )
        _ensure_applicant_match(context_name, user)
        return {
            "user": user,
            "roles": roles,
            "actor": "applicant",
            "context": context_row,
            "applicant_user": applicant_user,
            "portal_actor_user": user,
        }

    if roles & ALLOWED_STAFF_ROLES:
        if context_doctype == "Student Applicant":
            applicant_doc = frappe.get_doc("Student Applicant", context_name)
            if not frappe.has_permission("Student Applicant", ptype="read", doc=applicant_doc, user=user):
                frappe.throw(_("You do not have permission to access this applicant thread."), frappe.PermissionError)
        return {
            "user": user,
            "roles": roles,
            "actor": "staff",
            "context": context_row,
            "applicant_user": applicant_user,
        }

    frappe.throw(_("You do not have permission to access admissions communications."), frappe.PermissionError)
    return {}
