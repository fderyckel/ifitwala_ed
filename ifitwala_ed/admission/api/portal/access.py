# ifitwala_ed/admission/api/portal/access.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.access import (
    ADMISSIONS_FAMILY_ROLE,
    ADMISSIONS_PORTAL_ROLES,
    get_admissions_portal_applicant_names_for_user,
    is_family_workspace_enabled,
)

INVALID_SESSION_USERS = {"guest", "none", "null", "undefined"}

_DEFAULT_APPLICANT_PROFILE_FIELDS = (
    "student_preferred_name",
    "student_date_of_birth",
    "student_gender",
    "student_mobile_number",
    "student_joining_date",
    "student_first_language",
    "student_second_language",
    "student_nationality",
    "student_second_nationality",
    "residency_status",
)


def _as_text(value) -> str:
    return str(value or "").strip()


def _session_user() -> str:
    user = _as_text(getattr(frappe.session, "user", None)).strip()
    if not user:
        return ""
    if user.lower() in INVALID_SESSION_USERS:
        return ""
    return user


def _require_admissions_portal_user() -> str:
    user = _session_user()
    if not user:
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if not roles & ADMISSIONS_PORTAL_ROLES:
        frappe.throw(_("You do not have permission to access the admissions portal."), frappe.PermissionError)

    return user


def _require_admissions_applicant() -> str:
    return _require_admissions_portal_user()


def _get_applicant_rows_for_user(
    *,
    user: str,
    fields: list[str],
    limit: int = 25,
    include_promoted: bool = False,
) -> list[dict]:
    selected_fields = [field for field in fields if field]
    if "name" not in selected_fields:
        selected_fields = ["name", *selected_fields]

    applicant_names = get_admissions_portal_applicant_names_for_user(user=user, include_promoted=include_promoted)
    if not applicant_names:
        return []

    return frappe.get_all(
        "Student Applicant",
        filters={"name": ["in", applicant_names]},
        fields=selected_fields,
        limit=limit,
        order_by="creation asc",
    )


def _family_workspace_available_for_user(user: str) -> bool:
    roles = set(frappe.get_roles(user))
    return ADMISSIONS_FAMILY_ROLE in roles and is_family_workspace_enabled()


def _get_applicant_for_user(
    user: str,
    fields: list[str] | None = None,
    *,
    student_applicant: str | None = None,
) -> dict:
    fields = fields or [
        "name",
        "application_status",
        "organization",
        "school",
        "academic_year",
        "term",
        "program",
        "program_offering",
        "first_name",
        "middle_name",
        "last_name",
        *_DEFAULT_APPLICANT_PROFILE_FIELDS,
    ]
    rows = _get_applicant_rows_for_user(user=user, fields=fields, limit=50, include_promoted=False)
    if not rows:
        frappe.throw(
            _(
                "Admissions access is not linked to any active Applicant. Contact the admissions office to relink your account."
            ),
            frappe.PermissionError,
        )

    if student_applicant:
        for row in rows:
            if (row.get("name") or "").strip() == (student_applicant or "").strip():
                return row
        frappe.throw(_("You do not have permission to access this Applicant."), frappe.PermissionError)

    if len(rows) > 1 and not _family_workspace_available_for_user(user):
        frappe.log_error(
            title="Admissions Portal applicant identity conflict",
            message=frappe.as_json(
                {
                    "user": user,
                    "matched_applicants": sorted(
                        [_as_text(row.get("name")).strip() for row in rows if _as_text(row.get("name")).strip()]
                    ),
                }
            ),
        )
        frappe.throw(
            _(
                "Admissions access is linked to multiple Applicants. Contact the admissions office to relink your account."
            ),
            frappe.PermissionError,
        )
    return rows[0]


def _ensure_applicant_match(student_applicant: str | None, user: str) -> dict:
    return _get_applicant_for_user(user, student_applicant=student_applicant)
