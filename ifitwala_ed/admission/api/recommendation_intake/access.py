# ifitwala_ed/admission/api/recommendation_intake/access.py

from __future__ import annotations

import hashlib
import hmac

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from ifitwala_ed.admission.admission_utils import (
    has_open_applicant_review_access,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
)
from ifitwala_ed.admission.api.recommendation_intake.constants import (
    RECOMMENDATION_REQUEST_DOCTYPE,
    RECOMMENDATION_SUBMISSION_DOCTYPE,
    RECOMMENDATION_TEMPLATE_DOCTYPE,
    RECOMMENDATION_TEMPLATE_FIELD_DOCTYPE,
    REQUEST_STATUS_OPEN,
)


def _table_exists(doctype: str) -> bool:
    try:
        return bool(frappe.db.table_exists(doctype))
    except Exception:
        return False


def _feature_ready() -> bool:
    required = (
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        RECOMMENDATION_TEMPLATE_FIELD_DOCTYPE,
        RECOMMENDATION_REQUEST_DOCTYPE,
        RECOMMENDATION_SUBMISSION_DOCTYPE,
    )
    return all(_table_exists(doctype) for doctype in required)


def _require_feature_ready() -> None:
    if _feature_ready():
        return
    frappe.throw(_("Recommendation intake is not available yet. Please run migrations."))


def _get_bound_request():
    try:
        return frappe.request
    except RuntimeError:
        return None
    except Exception:
        return None


def _request_path_suffix(token: str) -> str:
    return f"/admissions/recommendation/{token}"


def _intake_url(token: str) -> str:
    return f"{frappe.utils.get_url()}{_request_path_suffix(token)}"


def _site_secret() -> str:
    return str(frappe.local.conf.get("encryption_key") or frappe.local.conf.get("secret") or frappe.local.site)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _otp_hash(*, request_name: str, otp_code: str) -> str:
    msg = f"{request_name}|{otp_code}".encode("utf-8")
    digest = hmac.new(_site_secret().encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return digest


def _request_by_token(token: str) -> dict:
    token = (token or "").strip()
    if not token:
        frappe.throw(_("Invalid recommendation link."), frappe.PermissionError)

    row = frappe.db.get_value(
        RECOMMENDATION_REQUEST_DOCTYPE,
        {"token_hash": _token_hash(token)},
        [
            "name",
            "student_applicant",
            "recommendation_template",
            "target_document_type",
            "applicant_document",
            "applicant_document_item",
            "item_key",
            "item_label",
            "request_status",
            "recommender_name",
            "recommender_email",
            "recommender_relationship",
            "expires_on",
            "consumed_on",
            "submission",
            "template_snapshot_json",
            "otp_enforced",
            "otp_code_hash",
            "otp_expires_on",
            "otp_verified_on",
            "otp_failed_attempts",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("This recommendation link is invalid."), frappe.PermissionError)

    status = (row.get("request_status") or "").strip()
    if status == "Revoked":
        frappe.throw(_("This recommendation link has been revoked."), frappe.PermissionError)

    expires_on = row.get("expires_on")
    if status in REQUEST_STATUS_OPEN and expires_on and get_datetime(expires_on) < now_datetime():
        frappe.db.set_value(
            RECOMMENDATION_REQUEST_DOCTYPE,
            row.get("name"),
            "request_status",
            "Expired",
            update_modified=False,
        )
        row["request_status"] = "Expired"
        status = "Expired"

    if status == "Expired":
        frappe.throw(_("This recommendation link has expired."), frappe.PermissionError)

    return row


def _applicant_for_user(user: str) -> dict:
    rows = frappe.get_all(
        "Student Applicant",
        filters={"applicant_user": user},
        fields=["name", "organization", "school"],
        limit=2,
    )
    if not rows:
        frappe.throw(_("Admissions access is not linked to any Applicant."), frappe.PermissionError)
    if len(rows) > 1:
        frappe.throw(_("Admissions access is linked to multiple Applicants."), frappe.PermissionError)
    return rows[0]


def _require_staff_recommendation_access(*, student_applicant: str | None = None, user: str | None = None) -> str:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        frappe.throw(_("You need to sign in to perform this action."), frappe.PermissionError)

    applicant_name = (student_applicant or "").strip()
    if is_admissions_file_staff_user(resolved_user):
        if applicant_name and not has_scoped_staff_access_to_student_applicant(
            user=resolved_user,
            student_applicant=applicant_name,
        ):
            frappe.throw(_("You do not have permission to access this Applicant."), frappe.PermissionError)
        return resolved_user

    if applicant_name and has_open_applicant_review_access(
        user=resolved_user,
        student_applicant=applicant_name,
    ):
        return resolved_user

    frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)
    return resolved_user
