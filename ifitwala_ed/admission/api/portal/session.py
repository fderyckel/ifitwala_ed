# ifitwala_ed/admission/api/portal/session.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.access import (
    ADMISSIONS_ACCESS_MODE_FAMILY,
    ADMISSIONS_PORTAL_ROLES,
    get_admissions_access_mode,
)
from ifitwala_ed.admission.api.portal.access import (
    _as_text,
    _get_applicant_for_user,
    _get_applicant_rows_for_user,
    _require_admissions_portal_user,
)
from ifitwala_ed.admission.api.portal.enrollment import (
    _portal_status_for,
    _read_only_for,
    _serialize_enrollment_offer,
)
from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
    get_latest_applicant_enrollment_plan,
)


def _build_applicant_display_name(row: dict) -> str:
    parts = [
        _as_text(row.get("first_name")).strip(),
        _as_text(row.get("middle_name")).strip(),
        _as_text(row.get("last_name")).strip(),
    ]
    name = " ".join(part for part in parts if part).strip()
    return name or _as_text(row.get("name")).strip()


def _applicant_summary_payload(row: dict) -> dict:
    portal_status = _portal_status_for(_as_text(row.get("application_status")).strip())
    is_read_only, reason = _read_only_for(_as_text(row.get("application_status")).strip())
    return {
        "name": row.get("name"),
        "display_name": _build_applicant_display_name(row),
        "portal_status": portal_status,
        "application_status": row.get("application_status"),
        "school": row.get("school"),
        "organization": row.get("organization"),
        "academic_year": row.get("academic_year"),
        "term": row.get("term"),
        "program": row.get("program"),
        "program_offering": row.get("program_offering"),
        "is_read_only": bool(is_read_only),
        "read_only_reason": reason,
    }


def get_admissions_session_impl(student_applicant: str | None = None):
    user = _require_admissions_portal_user()
    list_fields = [
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
    ]
    available_rows = _get_applicant_rows_for_user(user=user, fields=list_fields, limit=50, include_promoted=False)
    row = _get_applicant_for_user(user, fields=list_fields, student_applicant=student_applicant)
    latest_plan = get_latest_applicant_enrollment_plan(row.get("name"))
    enrollment_offer = _serialize_enrollment_offer(latest_plan)

    portal_status = _portal_status_for(row.get("application_status"), enrollment_offer)
    is_read_only, reason = _read_only_for(row.get("application_status"), enrollment_offer)

    user_row = frappe.db.get_value("User", user, ["name", "full_name"], as_dict=True) or {}
    roles = sorted(set(frappe.get_roles(user)) & ADMISSIONS_PORTAL_ROLES)

    return {
        "user": {
            "name": user_row.get("name") or user,
            "full_name": user_row.get("full_name") or user,
            "roles": roles,
        },
        "access_mode": get_admissions_access_mode(),
        "family_workspace_enabled": bool(get_admissions_access_mode() == ADMISSIONS_ACCESS_MODE_FAMILY),
        "selected_applicant": row.get("name"),
        "available_applicants": [_applicant_summary_payload(candidate) for candidate in available_rows],
        "applicant": {
            "name": row.get("name"),
            "display_name": _build_applicant_display_name(row),
            "portal_status": portal_status,
            "school": row.get("school"),
            "organization": row.get("organization"),
            "academic_year": row.get("academic_year"),
            "term": row.get("term"),
            "program": row.get("program"),
            "program_offering": row.get("program_offering"),
            "is_read_only": bool(is_read_only),
            "read_only_reason": reason,
        },
        "enrollment_offer": enrollment_offer,
    }
