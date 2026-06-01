# ifitwala_ed/admission/api/recommendation_intake/guest_intake.py

from __future__ import annotations

import random

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, now_datetime

from ifitwala_ed.admission import admissions_portal as admission_upload_api
from ifitwala_ed.admission.api.recommendation_intake.access import (
    _get_bound_request,
    _otp_hash,
    _request_by_token,
    _require_feature_ready,
)
from ifitwala_ed.admission.api.recommendation_intake.constants import (
    IDEMPOTENCY_TTL_SECONDS,
    OTP_MAX_FAILED_ATTEMPTS,
    OTP_TTL_MINUTES,
    RECOMMENDATION_REQUEST_DOCTYPE,
    RECOMMENDATION_SUBMISSION_DOCTYPE,
    REQUEST_STATUS_TERMINAL,
)
from ifitwala_ed.admission.api.recommendation_intake.document_integration import (
    _resolve_recommendation_upload_mime_hint,
)
from ifitwala_ed.admission.api.recommendation_intake.dto import (
    _as_bool,
    _normalize_answers,
    _normalize_payload,
    _parse_answers_payload,
)
from ifitwala_ed.admission.api.recommendation_intake.templates import _parse_snapshot


def get_recommendation_intake_payload(*, token: str | None = None):
    _require_feature_ready()
    token = (token or "").strip()
    row = _request_by_token(token)
    status = (row.get("request_status") or "").strip()

    if status == "Submitted":
        return {
            "status": "submitted",
            "already_submitted": True,
            "submitted_on": row.get("consumed_on"),
        }

    if status == "Sent":
        frappe.db.set_value(
            RECOMMENDATION_REQUEST_DOCTYPE,
            row.get("name"),
            {
                "request_status": "Opened",
                "opened_on": row.get("opened_on") or now_datetime(),
            },
            update_modified=False,
        )
        row["request_status"] = "Opened"
        row["opened_on"] = row.get("opened_on") or now_datetime()

    snapshot = _parse_snapshot(row.get("template_snapshot_json"), row.get("recommendation_template"))
    template = snapshot.get("template") or {}
    return {
        "status": "open",
        "already_submitted": False,
        "request": {
            "name": row.get("name"),
            "recommender_name": row.get("recommender_name"),
            "recommender_email": row.get("recommender_email"),
            "recommender_relationship": row.get("recommender_relationship"),
            "expires_on": row.get("expires_on"),
            "request_status": row.get("request_status"),
            "otp_enforced": bool(cint(row.get("otp_enforced"))),
            "otp_verified": bool(row.get("otp_verified_on")),
        },
        "template": {
            "name": template.get("name"),
            "template_name": template.get("template_name"),
            "allow_file_upload": bool(template.get("allow_file_upload")),
            "file_upload_required": bool(template.get("file_upload_required")),
            "otp_enforced": bool(template.get("otp_enforced")),
            "fields": snapshot.get("fields") or [],
        },
    }


def send_recommendation_otp(*, token: str | None = None):
    _require_feature_ready()
    token = (token or "").strip()
    row = _request_by_token(token)
    if not cint(row.get("otp_enforced")):
        frappe.throw(_("OTP verification is not required for this recommendation request."))
    if (row.get("request_status") or "").strip() in REQUEST_STATUS_TERMINAL:
        frappe.throw(_("This recommendation request is no longer open."), frappe.PermissionError)

    code = f"{random.randint(0, 999999):06d}"
    expires_on = add_to_date(now_datetime(), minutes=OTP_TTL_MINUTES, as_datetime=True)
    frappe.db.set_value(
        RECOMMENDATION_REQUEST_DOCTYPE,
        row.get("name"),
        {
            "otp_code_hash": _otp_hash(request_name=row.get("name"), otp_code=code),
            "otp_expires_on": expires_on,
            "otp_send_count": max(0, cint(row.get("otp_send_count") or 0)) + 1,
            "otp_failed_attempts": 0,
        },
        update_modified=False,
    )

    try:
        frappe.sendmail(
            recipients=[row.get("recommender_email")],
            subject=_("Recommendation verification code"),
            message=_("Your verification code is {otp_code}. It expires in {ttl_minutes} minutes.").format(
                otp_code=code,
                ttl_minutes=OTP_TTL_MINUTES,
            ),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Recommendation OTP send failed")
        frappe.throw(_("Unable to send OTP right now. Please try again."))

    response = {"ok": True, "otp_sent": True, "expires_on": expires_on}
    if cint(frappe.conf.get("developer_mode")):
        response["otp_code_debug"] = code
    return response


def _verify_otp_on_row(*, row: dict, otp_code: str) -> None:
    if not cint(row.get("otp_enforced")):
        return

    request_name = row.get("name")
    code_hash = (row.get("otp_code_hash") or "").strip()
    expires_on = row.get("otp_expires_on")
    failed_attempts = max(0, cint(row.get("otp_failed_attempts") or 0))
    if failed_attempts >= OTP_MAX_FAILED_ATTEMPTS:
        frappe.throw(_("Too many invalid OTP attempts. Request a new OTP code."), frappe.PermissionError)
    if not code_hash or not expires_on:
        frappe.throw(_("OTP verification is required. Request a new OTP code first."), frappe.PermissionError)
    if get_datetime(expires_on) < now_datetime():
        frappe.throw(_("OTP has expired. Request a new OTP code."), frappe.PermissionError)

    expected = _otp_hash(request_name=request_name, otp_code=(otp_code or "").strip())
    if expected != code_hash:
        frappe.db.set_value(
            RECOMMENDATION_REQUEST_DOCTYPE,
            request_name,
            "otp_failed_attempts",
            failed_attempts + 1,
            update_modified=False,
        )
        frappe.throw(_("Invalid OTP code."), frappe.PermissionError)

    frappe.db.set_value(
        RECOMMENDATION_REQUEST_DOCTYPE,
        request_name,
        {
            "otp_verified_on": now_datetime(),
            "otp_code_hash": None,
            "otp_expires_on": None,
            "otp_failed_attempts": 0,
        },
        update_modified=False,
    )


def verify_recommendation_otp(*, token: str | None = None, otp_code: str | None = None):
    _require_feature_ready()
    token = (token or "").strip()
    otp_code = (otp_code or "").strip()
    if not otp_code:
        frappe.throw(_("otp_code is required."), frappe.ValidationError)

    row = _request_by_token(token)
    if not cint(row.get("otp_enforced")):
        frappe.throw(_("OTP verification is not required for this recommendation request."))
    _verify_otp_on_row(row=row, otp_code=otp_code)
    return {"ok": True, "otp_verified": True}


def submit_recommendation(payload=None, **kwargs):
    _require_feature_ready()
    data = _normalize_payload(payload, kwargs)
    token = (data.get("token") or "").strip()
    if not token:
        frappe.throw(_("token is required."))
    client_request_id = (data.get("client_request_id") or "").strip() or None

    row = _request_by_token(token)
    request_name = row.get("name")
    status = (row.get("request_status") or "").strip()
    if status == "Submitted":
        return {
            "ok": True,
            "status": "already_processed",
            "idempotent": True,
            "recommendation_request": request_name,
            "submission": row.get("submission"),
        }

    cache = frappe.cache()
    idempotency_key = None
    if client_request_id:
        idempotency_key = f"ifitwala_ed:recommendation:submit:{request_name}:{client_request_id}"
        existing = cache.get_value(idempotency_key)
        if existing:
            parsed = frappe.parse_json(existing)
            if isinstance(parsed, dict):
                return {**parsed, "status": "already_processed", "idempotent": True}

    lock_key = f"ifitwala_ed:lock:recommendation:submit:{request_name}"
    with cache.lock(lock_key, timeout=20):
        if idempotency_key:
            existing = cache.get_value(idempotency_key)
            if existing:
                parsed = frappe.parse_json(existing)
                if isinstance(parsed, dict):
                    return {**parsed, "status": "already_processed", "idempotent": True}

        request_doc = frappe.get_doc(RECOMMENDATION_REQUEST_DOCTYPE, request_name)
        request_status = (request_doc.request_status or "").strip()
        if request_status == "Submitted":
            result = {
                "ok": True,
                "status": "already_processed",
                "idempotent": True,
                "recommendation_request": request_doc.name,
                "submission": request_doc.submission,
            }
            if idempotency_key:
                cache.set_value(idempotency_key, frappe.as_json(result), expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
            return result
        if request_status in {"Revoked", "Expired"}:
            frappe.throw(_("This recommendation request is no longer open."), frappe.PermissionError)

        if not _as_bool(data.get("attestation_confirmed")):
            frappe.throw(_("You must confirm the attestation before submitting."), frappe.ValidationError)

        snapshot = _parse_snapshot(request_doc.template_snapshot_json, request_doc.recommendation_template)
        answers = _parse_answers_payload(data)
        normalized_answers = _normalize_answers(snapshot, answers)
        template_meta = snapshot.get("template") or {}

        if cint(request_doc.otp_enforced) and not request_doc.otp_verified_on:
            otp_code = (data.get("otp_code") or "").strip()
            if not otp_code:
                frappe.throw(_("OTP verification is required before submission."), frappe.PermissionError)
            row_for_otp = frappe.db.get_value(
                RECOMMENDATION_REQUEST_DOCTYPE,
                request_doc.name,
                ["name", "otp_enforced", "otp_code_hash", "otp_expires_on", "otp_failed_attempts"],
                as_dict=True,
            )
            _verify_otp_on_row(row=row_for_otp or {}, otp_code=otp_code)
            request_doc.reload()

        request_obj = _get_bound_request()
        request_files = getattr(request_obj, "files", None) if request_obj else None
        uploaded_file = request_files.get("file") if request_files and hasattr(request_files, "get") else None
        has_file_in_request = bool(data.get("content")) or bool(uploaded_file)
        allow_file_upload = bool(template_meta.get("allow_file_upload"))
        file_upload_required = bool(template_meta.get("file_upload_required"))
        if has_file_in_request and not allow_file_upload:
            frappe.throw(_("This recommendation does not allow file uploads."), frappe.ValidationError)
        if file_upload_required and not has_file_in_request:
            frappe.throw(_("A file upload is required for this recommendation."), frappe.ValidationError)

        upload_result = None
        if has_file_in_request:
            upload_mime_hint = _resolve_recommendation_upload_mime_hint(
                file_name=data.get("file_name") or getattr(uploaded_file, "filename", None),
                content_type=(
                    data.get("mime_type_hint")
                    or data.get("content_type")
                    or getattr(uploaded_file, "mimetype", None)
                    or getattr(uploaded_file, "content_type", None)
                ),
            )
            upload_payload = {
                "student_applicant": request_doc.student_applicant,
                "document_type": request_doc.target_document_type,
                "applicant_document": request_doc.applicant_document,
                "applicant_document_item": request_doc.applicant_document_item,
                "item_key": request_doc.item_key,
                "item_label": request_doc.item_label,
                "upload_source": "API",
                "is_private": 1,
                "client_request_id": client_request_id,
                "mime_type_hint": upload_mime_hint,
            }
            if data.get("content"):
                upload_payload["content"] = data.get("content")
            if data.get("file_name"):
                upload_payload["file_name"] = data.get("file_name")
            upload_result = admission_upload_api.upload_applicant_document(**upload_payload)

        submission_doc = frappe.get_doc(
            {
                "doctype": RECOMMENDATION_SUBMISSION_DOCTYPE,
                "recommendation_request": request_doc.name,
                "student_applicant": request_doc.student_applicant,
                "recommendation_template": request_doc.recommendation_template,
                "applicant_document": (
                    (upload_result or {}).get("applicant_document") or request_doc.applicant_document or None
                ),
                "applicant_document_item": (
                    (upload_result or {}).get("applicant_document_item") or request_doc.applicant_document_item or None
                ),
                "recommender_name": request_doc.recommender_name,
                "recommender_email": request_doc.recommender_email,
                "answers_json": frappe.as_json(normalized_answers),
                "attestation_confirmed": 1,
                "has_file": 1 if has_file_in_request else 0,
                "submitted_on": now_datetime(),
                "source_ip": getattr(frappe.local, "request_ip", None),
                "user_agent": (
                    request_obj.headers.get("User-Agent")
                    if request_obj and getattr(request_obj, "headers", None)
                    else None
                ),
                "idempotency_key": client_request_id,
            }
        )
        submission_doc.insert(ignore_permissions=True)

        request_doc.request_status = "Submitted"
        request_doc.consumed_on = now_datetime()
        request_doc.submission = submission_doc.name
        if upload_result:
            request_doc.applicant_document = upload_result.get("applicant_document") or request_doc.applicant_document
            request_doc.applicant_document_item = (
                upload_result.get("applicant_document_item") or request_doc.applicant_document_item
            )
        request_doc.save(ignore_permissions=True)

        applicant = frappe.get_doc("Student Applicant", request_doc.student_applicant)
        applicant.add_comment(
            "Comment",
            text=_("Recommendation submitted for request {request_name}.").format(
                request_name=frappe.bold(request_doc.name)
            ),
        )

        result = {
            "ok": True,
            "status": "processed",
            "idempotent": False,
            "recommendation_request": request_doc.name,
            "submission": submission_doc.name,
            "has_file": bool(has_file_in_request),
            "applicant_document": request_doc.applicant_document,
            "applicant_document_item": request_doc.applicant_document_item,
        }
        if idempotency_key:
            cache.set_value(idempotency_key, frappe.as_json(result), expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return result
