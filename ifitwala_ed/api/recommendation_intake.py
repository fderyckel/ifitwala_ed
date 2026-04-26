# ifitwala_ed/api/recommendation_intake.py

from __future__ import annotations

import hashlib
import hmac
import random

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, now_datetime

from ifitwala_ed.admission import admissions_portal as admission_upload_api
from ifitwala_ed.admission.admission_utils import (
    ensure_admissions_permission,
    get_applicant_scope_ancestors,
    has_open_applicant_review_access,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
    is_applicant_document_type_in_scope,
    normalize_email_value,
)
from ifitwala_ed.api.attachment_previews import build_attachment_preview_item, extract_file_extension
from ifitwala_ed.api.file_access import (
    get_drive_file_thumbnail_ready_map,
    resolve_admissions_file_open_url,
    resolve_admissions_file_preview_url,
    resolve_admissions_file_thumbnail_url,
)
from ifitwala_ed.integrations.drive.authority import get_current_drive_files_for_attachments

ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
RECOMMENDATION_TEMPLATE_DOCTYPE = "Recommendation Template"
RECOMMENDATION_TEMPLATE_FIELD_DOCTYPE = "Recommendation Template Field"
RECOMMENDATION_REQUEST_DOCTYPE = "Recommendation Request"
RECOMMENDATION_SUBMISSION_DOCTYPE = "Recommendation Submission"
REQUEST_STATUS_OPEN = {"Sent", "Opened"}
REQUEST_STATUS_TERMINAL = {"Submitted", "Revoked", "Expired"}
REQUEST_STATUS_ALL = REQUEST_STATUS_OPEN | REQUEST_STATUS_TERMINAL
TOKEN_DEFAULT_EXPIRY_DAYS = 14
TOKEN_MAX_EXPIRY_DAYS = 60
OTP_TTL_MINUTES = 10
OTP_MAX_FAILED_ATTEMPTS = 5
IDEMPOTENCY_TTL_SECONDS = 60 * 15


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


def _normalize_payload(payload, kwargs):
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        frappe.throw(_("payload must be a JSON object."))
    data = dict(payload)
    for key, value in (kwargs or {}).items():
        if key in data:
            continue
        data[key] = value
    return data


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def _text(value) -> str:
    return str(value or "").strip()


def _load_drive_version_mime_map(version_ids: list[str]) -> dict[str, str]:
    resolved_version_ids = [version_id for version_id in dict.fromkeys(version_ids) if _text(version_id)]
    if not resolved_version_ids:
        return {}

    rows = frappe.get_all(
        "Drive File Version",
        filters={"name": ["in", resolved_version_ids]},
        fields=["name", "mime_type"],
        limit=0,
    )
    return {_text(row.get("name")): _text(row.get("mime_type")) for row in rows if _text(row.get("name"))}


def _serialize_recommendation_attachment(
    *,
    student_applicant: str,
    latest_drive_file: dict | None,
    thumbnail_ready_map: dict[str, bool],
    version_mime_map: dict[str, str],
) -> dict:
    drive_row = latest_drive_file or {}
    drive_file_id = _text(drive_row.get("name"))
    compatibility_file_id = _text(drive_row.get("file"))
    canonical_ref = _text(drive_row.get("canonical_ref")) or None
    file_name = (
        _text(drive_row.get("display_name")) or _text(drive_row.get("file_name")) or compatibility_file_id or None
    )
    preview_status = _text(drive_row.get("preview_status")) or None
    if not drive_file_id and not compatibility_file_id:
        return {
            "drive_file_id": None,
            "canonical_ref": None,
            "file_name": None,
            "open_url": None,
            "preview_url": None,
            "thumbnail_url": None,
            "preview_status": None,
            "attachment_preview": None,
        }

    open_url = resolve_admissions_file_open_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id or None,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant,
    )
    preview_url = resolve_admissions_file_preview_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id or None,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant,
        preview_ready=preview_status == "ready",
    )
    thumbnail_url = resolve_admissions_file_thumbnail_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id or None,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant,
        thumbnail_ready=thumbnail_ready_map.get(drive_file_id, False),
    )
    mime_type = version_mime_map.get(_text(drive_row.get("current_version"))) or None
    attachment_preview = build_attachment_preview_item(
        item_id=drive_file_id or compatibility_file_id or file_name,
        owner_doctype="Student Applicant",
        owner_name=student_applicant,
        file_id=drive_file_id or compatibility_file_id,
        display_name=file_name,
        mime_type=mime_type,
        extension=extract_file_extension(file_name=file_name, file_url=None),
        preview_status=preview_status,
        thumbnail_url=thumbnail_url,
        preview_url=preview_url,
        open_url=open_url,
        download_url=open_url,
    )
    return {
        "drive_file_id": drive_file_id or None,
        "canonical_ref": canonical_ref,
        "file_name": file_name,
        "open_url": open_url,
        "preview_url": preview_url,
        "thumbnail_url": thumbnail_url,
        "preview_status": preview_status,
        "attachment_preview": attachment_preview,
    }


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


def _parse_select_options(text: str | None) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    try:
        parsed = frappe.parse_json(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item or "").strip()]
    except Exception:
        pass
    tokens = []
    for line in raw.split("\n"):
        for chunk in line.split(","):
            token = chunk.strip()
            if token:
                tokens.append(token)
    return tokens


def _template_snapshot(template_name: str) -> dict:
    template = frappe.db.get_value(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        template_name,
        [
            "name",
            "template_name",
            "allow_file_upload",
            "file_upload_required",
            "otp_enforced",
            "minimum_required",
            "maximum_allowed",
            "applicant_can_view_status",
            "target_document_type",
        ],
        as_dict=True,
    )
    if not template:
        frappe.throw(_("Recommendation Template no longer exists."))

    rows = frappe.get_all(
        RECOMMENDATION_TEMPLATE_FIELD_DOCTYPE,
        filters={"parenttype": RECOMMENDATION_TEMPLATE_DOCTYPE, "parent": template_name},
        fields=["field_key", "label", "field_type", "is_required", "options_json", "help_text", "idx"],
        order_by="idx asc",
    )

    fields = []
    for row in rows:
        field_key = frappe.scrub((row.get("field_key") or "").strip())[:80]
        if not field_key:
            continue
        field_type = (row.get("field_type") or "Data").strip()
        fields.append(
            {
                "field_key": field_key,
                "label": (row.get("label") or "").strip() or field_key,
                "field_type": field_type,
                "is_required": bool(cint(row.get("is_required"))),
                "options": _parse_select_options(row.get("options_json")),
                "help_text": (row.get("help_text") or "").strip(),
            }
        )

    return {
        "template": {
            "name": template.get("name"),
            "template_name": (template.get("template_name") or "").strip() or template.get("name"),
            "allow_file_upload": bool(cint(template.get("allow_file_upload"))),
            "file_upload_required": bool(cint(template.get("file_upload_required"))),
            "otp_enforced": bool(cint(template.get("otp_enforced"))),
            "minimum_required": max(0, cint(template.get("minimum_required") or 0)),
            "maximum_allowed": max(1, cint(template.get("maximum_allowed") or 1)),
            "applicant_can_view_status": bool(cint(template.get("applicant_can_view_status"))),
            "target_document_type": (template.get("target_document_type") or "").strip(),
        },
        "fields": fields,
    }


def _request_scope_ancestors(student_applicant: str) -> tuple[dict, set[str], set[str]]:
    applicant_row = frappe.db.get_value(
        "Student Applicant",
        student_applicant,
        ["name", "organization", "school", "application_status"],
        as_dict=True,
    )
    if not applicant_row:
        frappe.throw(_("Invalid Student Applicant: {student_applicant}.").format(student_applicant=student_applicant))

    org_scope, school_scope = get_applicant_scope_ancestors(
        organization=applicant_row.get("organization"),
        school=applicant_row.get("school"),
    )
    return applicant_row, set(org_scope), set(school_scope)


def _template_in_scope(*, template_row: dict, org_scope: set[str], school_scope: set[str]) -> bool:
    template_org = (template_row.get("organization") or "").strip()
    template_school = (template_row.get("school") or "").strip()
    if template_org and template_org not in org_scope:
        return False
    if template_school and template_school not in school_scope:
        return False
    return True


def _ensure_template_scope_for_applicant(*, student_applicant: str, template_name: str) -> tuple[dict, dict]:
    applicant_row, org_scope, school_scope = _request_scope_ancestors(student_applicant)
    template_row = frappe.db.get_value(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        template_name,
        [
            "name",
            "is_active",
            "organization",
            "school",
            "target_document_type",
            "minimum_required",
            "maximum_allowed",
            "allow_file_upload",
            "file_upload_required",
            "otp_enforced",
            "applicant_can_view_status",
        ],
        as_dict=True,
    )
    if not template_row:
        frappe.throw(_("Invalid Recommendation Template: {template_name}.").format(template_name=template_name))
    if not cint(template_row.get("is_active")):
        frappe.throw(_("Recommendation Template is inactive."))
    if not _template_in_scope(template_row=template_row, org_scope=org_scope, school_scope=school_scope):
        frappe.throw(_("Recommendation Template is outside the Applicant scope."))

    target_document_type = (template_row.get("target_document_type") or "").strip()
    if not target_document_type:
        frappe.throw(_("Recommendation Template target document type is required."))
    target_row = frappe.db.get_value(
        "Applicant Document Type",
        target_document_type,
        ["name", "is_active", "organization", "school", "is_repeatable"],
        as_dict=True,
    )
    if not target_row:
        frappe.throw(_("Recommendation target document type no longer exists."))
    if not cint(target_row.get("is_active")):
        frappe.throw(_("Recommendation target document type must be active."))
    if not is_applicant_document_type_in_scope(
        document_type_organization=target_row.get("organization"),
        document_type_school=target_row.get("school"),
        applicant_org_ancestors=org_scope,
        applicant_school_ancestors=school_scope,
    ):
        frappe.throw(_("Recommendation target document type is outside the Applicant scope."))

    max_allowed = max(1, cint(template_row.get("maximum_allowed") or 1))
    if max_allowed > 1 and not cint(target_row.get("is_repeatable")):
        frappe.throw(_("Recommendation target document type must be repeatable for multiple letters."))

    return applicant_row, template_row


def get_recommendation_template_rows_for_applicant(
    *,
    student_applicant: str,
    include_confidential: bool = False,
    fields: list[str] | tuple[str, ...] | None = None,
) -> list[dict]:
    if not _feature_ready():
        return []

    student_applicant = (student_applicant or "").strip()
    if not student_applicant:
        return []

    request_scope = _request_scope_ancestors(student_applicant)
    org_scope = request_scope[1]
    school_scope = request_scope[2]

    required_fields = ["name", "organization", "school"]
    if not include_confidential:
        required_fields.append("applicant_can_view_status")
    query_fields = list(dict.fromkeys(required_fields + list(fields or [])))

    rows = frappe.get_all(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        filters={"is_active": 1},
        fields=query_fields,
    )

    template_rows = []
    for row in rows:
        if not _template_in_scope(template_row=row, org_scope=org_scope, school_scope=school_scope):
            continue
        if not include_confidential and not cint(row.get("applicant_can_view_status")):
            continue
        template_rows.append(row)
    return template_rows


def _new_item_key(student_applicant: str) -> str:
    base = "recommendation"
    for _index in range(30):
        candidate = f"{base}_{frappe.generate_hash(length=8)}"
        if not frappe.db.exists(
            RECOMMENDATION_REQUEST_DOCTYPE,
            {"student_applicant": student_applicant, "item_key": candidate},
        ):
            return candidate
    frappe.throw(_("Could not allocate a unique recommendation item key."))
    return ""


def _ensure_document_item_slot(
    *,
    student_applicant: str,
    target_document_type: str,
    item_key: str,
    item_label: str,
) -> tuple[str, str]:
    doc_name = frappe.db.get_value(
        "Applicant Document",
        {"student_applicant": student_applicant, "document_type": target_document_type},
        "name",
    )
    if not doc_name:
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": student_applicant,
                "document_type": target_document_type,
            }
        )
        doc.insert(ignore_permissions=True)
        doc_name = doc.name

    item_name = frappe.db.get_value(
        "Applicant Document Item",
        {"applicant_document": doc_name, "item_key": item_key},
        "name",
    )
    if not item_name:
        item = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": doc_name,
                "item_key": item_key,
                "item_label": item_label,
            }
        )
        item.insert(ignore_permissions=True)
        item_name = item.name
    else:
        frappe.db.set_value(
            "Applicant Document Item",
            item_name,
            "item_label",
            item_label,
            update_modified=False,
        )

    return doc_name, item_name


def _send_recommendation_request_email(*, request_row: dict, intake_url: str, is_resend: bool) -> bool:
    recipient = normalize_email_value(request_row.get("recommender_email"))
    if not recipient:
        return False
    subject = _("Recommendation Request for Applicant")
    status_label = _("resend") if is_resend else _("new request")
    message = _(
        "You have received a {status_label}. Use this secure link to submit the recommendation before {expires_on}: {intake_url}"
    ).format(
        status_label=status_label,
        expires_on=request_row.get("expires_on"),
        intake_url=intake_url,
    )
    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
        )
        return True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Recommendation request email failed")
        return False


def _refresh_expired_requests(*, student_applicant: str | None = None) -> None:
    if not _table_exists(RECOMMENDATION_REQUEST_DOCTYPE):
        return
    now_value = now_datetime()
    filters_sql = ""
    params = {"now": now_value}
    if student_applicant:
        filters_sql = " AND student_applicant = %(student_applicant)s"
        params["student_applicant"] = student_applicant

    frappe.db.sql(
        f"""
        UPDATE `tab{RECOMMENDATION_REQUEST_DOCTYPE}`
           SET request_status = 'Expired'
         WHERE request_status IN ('Sent', 'Opened')
           AND expires_on < %(now)s
           {filters_sql}
        """,
        params,
    )


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


def _parse_snapshot(snapshot_json: str | None, template_name: str) -> dict:
    if snapshot_json:
        try:
            parsed = frappe.parse_json(snapshot_json)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return _template_snapshot(template_name)


def _normalize_answers(snapshot: dict, answers: dict) -> dict:
    if not isinstance(answers, dict):
        frappe.throw(_("answers must be an object."), frappe.ValidationError)

    normalized = {}
    fields = snapshot.get("fields") or []
    for field in fields:
        key = (field.get("field_key") or "").strip()
        label = (field.get("label") or key).strip()
        field_type = (field.get("field_type") or "Data").strip()
        required = bool(field.get("is_required"))
        options = [str(option).strip() for option in (field.get("options") or []) if str(option).strip()]
        raw_value = answers.get(key)

        if field_type == "Check":
            value = 1 if _as_bool(raw_value) else 0
            if required and not value:
                frappe.throw(
                    _("Required field is missing: {field_label}.").format(field_label=label),
                    frappe.ValidationError,
                )
        else:
            value = "" if raw_value is None else str(raw_value).strip()
            if required and not value:
                frappe.throw(
                    _("Required field is missing: {field_label}.").format(field_label=label),
                    frappe.ValidationError,
                )
            if field_type == "Select" and value and options and value not in options:
                frappe.throw(
                    _("Invalid option for {field_label}.").format(field_label=label),
                    frappe.ValidationError,
                )

        normalized[key] = {
            "label": label,
            "field_type": field_type,
            "value": value,
        }

    return normalized


def _parse_answers_payload(data: dict) -> dict:
    answers = data.get("answers")
    if answers is None:
        answers = data.get("answers_json")

    if isinstance(answers, str):
        text = answers.strip()
        if not text:
            return {}
        parsed = frappe.parse_json(text)
        if isinstance(parsed, dict):
            return parsed
        frappe.throw(_("answers must be a JSON object."), frappe.ValidationError)
    if isinstance(answers, dict):
        return answers
    if answers is None:
        return {}
    frappe.throw(_("answers must be a JSON object."), frappe.ValidationError)
    return {}


def _summary_from_rows(rows: list[dict], *, required_total: int, received_total: int) -> dict:
    counts = {status: 0 for status in sorted(REQUEST_STATUS_ALL)}
    for row in rows:
        status = (row.get("request_status") or "").strip()
        if status in counts:
            counts[status] += 1
    state = "optional"
    if required_total > 0:
        if received_total >= required_total:
            state = "complete"
        elif received_total > 0:
            state = "in_progress"
        else:
            state = "pending"
    return {
        "counts": counts,
        "required_total": required_total,
        "received_total": received_total,
        "state": state,
    }


def _default_recommendation_status_payload(*, include_confidential: bool = False) -> dict:
    payload = {
        "ok": True,
        "required_total": 0,
        "received_total": 0,
        "requested_total": 0,
        "missing": [],
        "rows": [],
        "state": "optional",
        "counts": {status: 0 for status in sorted(REQUEST_STATUS_ALL)},
    }
    if include_confidential:
        payload.update(
            {
                "review_rows": [],
                "pending_review_count": 0,
                "first_pending_review": None,
                "latest_submitted_on": None,
            }
        )
    return payload


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


def _sort_datetime_value(value) -> str:
    if not value:
        return ""
    try:
        return get_datetime(value).isoformat()
    except Exception:
        return str(value or "")


def _render_recommendation_answer_value(field_type: str, value) -> str:
    normalized_type = (field_type or "Data").strip()
    if normalized_type == "Check":
        return _("Yes") if cint(value) else _("No")
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _build_recommendation_answer_rows(snapshot: dict, answers_json: str | None) -> list[dict]:
    parsed_answers = {}
    if answers_json:
        try:
            candidate = frappe.parse_json(answers_json)
            if isinstance(candidate, dict):
                parsed_answers = candidate
        except Exception:
            parsed_answers = {}

    rows: list[dict] = []
    seen_keys: set[str] = set()

    for field in snapshot.get("fields") or []:
        field_key = frappe.scrub((field.get("field_key") or "").strip())[:80]
        if not field_key:
            continue

        answer_entry = parsed_answers.get(field_key)
        if isinstance(answer_entry, dict):
            value = answer_entry.get("value")
            label = (answer_entry.get("label") or field.get("label") or field_key).strip()
            field_type = (answer_entry.get("field_type") or field.get("field_type") or "Data").strip()
        else:
            value = answer_entry
            label = (field.get("label") or field_key).strip()
            field_type = (field.get("field_type") or "Data").strip()

        display_value = _render_recommendation_answer_value(field_type, value)
        rows.append(
            {
                "field_key": field_key,
                "label": label or field_key,
                "field_type": field_type,
                "value": value,
                "display_value": display_value,
                "has_value": True if field_type == "Check" else bool(display_value),
            }
        )
        seen_keys.add(field_key)

    for field_key, answer_entry in parsed_answers.items():
        normalized_key = frappe.scrub((field_key or "").strip())[:80]
        if not normalized_key or normalized_key in seen_keys:
            continue

        if isinstance(answer_entry, dict):
            value = answer_entry.get("value")
            label = (answer_entry.get("label") or normalized_key).strip()
            field_type = (answer_entry.get("field_type") or "Data").strip()
        else:
            value = answer_entry
            label = normalized_key
            field_type = "Data"

        display_value = _render_recommendation_answer_value(field_type, value)
        rows.append(
            {
                "field_key": normalized_key,
                "label": label or normalized_key,
                "field_type": field_type,
                "value": value,
                "display_value": display_value,
                "has_value": True if field_type == "Check" else bool(display_value),
            }
        )

    return rows


def get_recommendation_status_batch_for_applicants(
    *,
    applicant_rows: list[dict],
    include_confidential: bool = False,
) -> dict[str, dict]:
    normalized_applicants: list[dict] = []
    applicant_names: list[str] = []
    seen_names: set[str] = set()
    for row in applicant_rows or []:
        applicant_name = (row.get("name") or "").strip()
        if not applicant_name or applicant_name in seen_names:
            continue
        seen_names.add(applicant_name)
        normalized_row = {
            "name": applicant_name,
            "organization": (row.get("organization") or "").strip(),
            "school": (row.get("school") or "").strip(),
        }
        normalized_applicants.append(normalized_row)
        applicant_names.append(applicant_name)

    if not applicant_names:
        return {}

    if not _feature_ready():
        return {
            applicant_name: _default_recommendation_status_payload(include_confidential=include_confidential)
            for applicant_name in applicant_names
        }

    template_query_fields = ["name", "template_name", "minimum_required", "organization", "school"]
    if not include_confidential:
        template_query_fields.append("applicant_can_view_status")

    active_template_rows = frappe.get_all(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        filters={"is_active": 1},
        fields=template_query_fields,
        limit=10000,
    )

    scope_cache: dict[tuple[str, str], tuple[set[str], set[str]]] = {}
    templates_by_applicant: dict[str, list[dict]] = {}
    active_template_names: set[str] = set()

    for applicant_row in normalized_applicants:
        organization = applicant_row.get("organization")
        school = applicant_row.get("school")
        applicant_name = applicant_row.get("name")

        scope_key = (organization or "", school or "")
        if scope_key not in scope_cache:
            org_scope, school_scope = get_applicant_scope_ancestors(
                organization=organization,
                school=school,
            )
            scope_cache[scope_key] = (set(org_scope), set(school_scope))

        org_scope, school_scope = scope_cache[scope_key]
        in_scope_templates: list[dict] = []
        for template_row in active_template_rows:
            if not _template_in_scope(template_row=template_row, org_scope=org_scope, school_scope=school_scope):
                continue
            if not include_confidential and not cint(template_row.get("applicant_can_view_status")):
                continue
            in_scope_templates.append(template_row)
            template_name = (template_row.get("name") or "").strip()
            if template_name:
                active_template_names.add(template_name)

        templates_by_applicant[applicant_name] = in_scope_templates

    summary_request_rows = []
    if active_template_names:
        summary_request_rows = frappe.get_all(
            RECOMMENDATION_REQUEST_DOCTYPE,
            filters={
                "student_applicant": ["in", applicant_names],
                "recommendation_template": ["in", sorted(active_template_names)],
            },
            fields=["student_applicant", "recommendation_template", "request_status"],
            limit=10000,
        )

    grouped_statuses_by_applicant: dict[str, dict[str, list[str]]] = {
        applicant_name: {} for applicant_name in applicant_names
    }
    status_counts_by_applicant: dict[str, dict[str, int]] = {
        applicant_name: {status: 0 for status in sorted(REQUEST_STATUS_ALL)} for applicant_name in applicant_names
    }

    for request_row in summary_request_rows:
        applicant_name = (request_row.get("student_applicant") or "").strip()
        template_name = (request_row.get("recommendation_template") or "").strip()
        if not applicant_name or not template_name:
            continue
        status = (request_row.get("request_status") or "").strip()
        grouped_statuses_by_applicant.setdefault(applicant_name, {}).setdefault(template_name, []).append(status)
        if status in status_counts_by_applicant.get(applicant_name, {}):
            status_counts_by_applicant[applicant_name][status] += 1

    review_rows_by_applicant: dict[str, list[dict]] = {applicant_name: [] for applicant_name in applicant_names}
    pending_review_count_by_applicant: dict[str, int] = {applicant_name: 0 for applicant_name in applicant_names}
    first_pending_review_by_applicant: dict[str, dict | None] = {
        applicant_name: None for applicant_name in applicant_names
    }
    latest_submitted_on_by_applicant: dict[str, object | None] = {
        applicant_name: None for applicant_name in applicant_names
    }

    if include_confidential and frappe.db.table_exists(RECOMMENDATION_REQUEST_DOCTYPE):
        review_request_rows = frappe.get_all(
            RECOMMENDATION_REQUEST_DOCTYPE,
            filters={"student_applicant": ["in", applicant_names]},
            fields=[
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
                "sent_on",
                "opened_on",
                "consumed_on",
                "resend_count",
                "submission",
            ],
            order_by="consumed_on desc, modified desc",
            limit=10000,
        )

        review_template_names = sorted(
            {
                (row.get("recommendation_template") or "").strip()
                for row in review_request_rows
                if (row.get("recommendation_template") or "").strip()
            }
        )
        review_template_map = {}
        if review_template_names:
            review_template_map = {
                (row.get("name") or "").strip(): row
                for row in frappe.get_all(
                    RECOMMENDATION_TEMPLATE_DOCTYPE,
                    filters={"name": ["in", review_template_names]},
                    fields=["name", "template_name"],
                    limit=len(review_template_names),
                )
                if (row.get("name") or "").strip()
            }

        submission_by_request: dict[str, dict] = {}
        submission_names = [
            (row.get("submission") or "").strip()
            for row in review_request_rows
            if (row.get("submission") or "").strip()
        ]
        if submission_names and frappe.db.table_exists(RECOMMENDATION_SUBMISSION_DOCTYPE):
            submission_rows = frappe.get_all(
                RECOMMENDATION_SUBMISSION_DOCTYPE,
                filters={"name": ["in", sorted(set(submission_names))]},
                fields=[
                    "name",
                    "recommendation_request",
                    "applicant_document",
                    "applicant_document_item",
                    "submitted_on",
                    "has_file",
                    "attestation_confirmed",
                ],
                limit=len(set(submission_names)),
            )
            submission_by_request = {
                (row.get("recommendation_request") or "").strip(): row
                for row in submission_rows
                if (row.get("recommendation_request") or "").strip()
            }

        applicant_document_item_names = sorted(
            {
                (submission_by_request.get((row.get("name") or "").strip()) or {}).get("applicant_document_item")
                or row.get("applicant_document_item")
                for row in review_request_rows
                if (
                    (submission_by_request.get((row.get("name") or "").strip()) or {}).get("applicant_document_item")
                    or row.get("applicant_document_item")
                )
            }
        )
        item_map = {}
        if applicant_document_item_names:
            item_rows = frappe.get_all(
                "Applicant Document Item",
                filters={"name": ["in", applicant_document_item_names]},
                fields=["name", "review_status", "reviewed_by", "reviewed_on"],
                limit=len(applicant_document_item_names),
            )
            item_map = {(row.get("name") or "").strip(): row for row in item_rows if (row.get("name") or "").strip()}

        latest_drive_file_by_item = {}
        if applicant_document_item_names:
            drive_rows = get_current_drive_files_for_attachments(
                attached_doctype="Applicant Document Item",
                attached_names=applicant_document_item_names,
                fields=[
                    "name",
                    "attached_name",
                    "file",
                    "canonical_ref",
                    "display_name",
                    "preview_status",
                    "current_version",
                    "creation",
                ],
                statuses=("active", "processing", "blocked"),
            )
            for drive_row in drive_rows:
                attached_to_name = _text(drive_row.get("attached_name"))
                if not attached_to_name or attached_to_name in latest_drive_file_by_item:
                    continue
                latest_drive_file_by_item[attached_to_name] = drive_row

        drive_thumbnail_ready_map = get_drive_file_thumbnail_ready_map(
            [
                _text(row_drive.get("name"))
                for row_drive in latest_drive_file_by_item.values()
                if _text(row_drive.get("name"))
            ]
        )
        drive_version_mime_map = _load_drive_version_mime_map(
            [
                _text(row_drive.get("current_version"))
                for row_drive in latest_drive_file_by_item.values()
                if _text(row_drive.get("current_version"))
            ]
        )

        for request_row in review_request_rows:
            applicant_name = (request_row.get("student_applicant") or "").strip()
            request_name = (request_row.get("name") or "").strip()
            if not applicant_name or not request_name:
                continue

            submission_row = submission_by_request.get(request_name) or {}
            applicant_document_item = (submission_row.get("applicant_document_item") or "").strip() or (
                request_row.get("applicant_document_item") or ""
            ).strip()
            item_row = item_map.get(applicant_document_item) or {}
            review_status = (item_row.get("review_status") or "").strip() or "Pending"
            latest_attachment = _serialize_recommendation_attachment(
                student_applicant=applicant_name,
                latest_drive_file=latest_drive_file_by_item.get(applicant_document_item),
                thumbnail_ready_map=drive_thumbnail_ready_map,
                version_mime_map=drive_version_mime_map,
            )
            submitted_on = submission_row.get("submitted_on") or request_row.get("consumed_on")
            template_name = (request_row.get("recommendation_template") or "").strip()
            template_meta = review_template_map.get(template_name) or {}
            needs_review = (
                request_row.get("request_status") or ""
            ).strip() == "Submitted" and review_status == "Pending"

            review_row = {
                "recommendation_request": request_name,
                "recommendation_submission": (submission_row.get("name") or "").strip() or None,
                "student_applicant": applicant_name,
                "recommendation_template": template_name or None,
                "template_name": (template_meta.get("template_name") or template_name or "").strip() or None,
                "target_document_type": (request_row.get("target_document_type") or "").strip() or None,
                "applicant_document": (
                    (submission_row.get("applicant_document") or "").strip()
                    or (request_row.get("applicant_document") or "").strip()
                    or None
                ),
                "applicant_document_item": applicant_document_item or None,
                "item_key": (request_row.get("item_key") or "").strip() or None,
                "item_label": (request_row.get("item_label") or "").strip() or None,
                "request_status": (request_row.get("request_status") or "").strip() or None,
                "review_status": review_status,
                "reviewed_by": (item_row.get("reviewed_by") or "").strip() or None,
                "reviewed_on": item_row.get("reviewed_on"),
                "recommender_name": (request_row.get("recommender_name") or "").strip() or None,
                "recommender_email": (request_row.get("recommender_email") or "").strip() or None,
                "recommender_relationship": (request_row.get("recommender_relationship") or "").strip() or None,
                "sent_on": request_row.get("sent_on"),
                "opened_on": request_row.get("opened_on"),
                "submitted_on": submitted_on,
                "expires_on": request_row.get("expires_on"),
                "resend_count": cint(request_row.get("resend_count") or 0),
                "has_file": bool(cint(submission_row.get("has_file"))),
                "attestation_confirmed": bool(cint(submission_row.get("attestation_confirmed"))),
                "file_name": latest_attachment.get("file_name"),
                "open_url": latest_attachment.get("open_url"),
                "preview_url": latest_attachment.get("preview_url"),
                "thumbnail_url": latest_attachment.get("thumbnail_url"),
                "preview_status": latest_attachment.get("preview_status"),
                "drive_file_id": latest_attachment.get("drive_file_id"),
                "canonical_ref": latest_attachment.get("canonical_ref"),
                "attachment_preview": latest_attachment.get("attachment_preview"),
                "needs_review": bool(needs_review),
                "can_review": bool(
                    (request_row.get("request_status") or "").strip() == "Submitted" and applicant_document_item
                ),
            }
            review_rows_by_applicant.setdefault(applicant_name, []).append(review_row)

            if submitted_on and not latest_submitted_on_by_applicant.get(applicant_name):
                latest_submitted_on_by_applicant[applicant_name] = submitted_on

            if needs_review:
                pending_review_count_by_applicant[applicant_name] = (
                    pending_review_count_by_applicant.get(applicant_name, 0) + 1
                )
                if not first_pending_review_by_applicant.get(applicant_name):
                    first_pending_review_by_applicant[applicant_name] = {
                        "recommendation_request": review_row.get("recommendation_request"),
                        "recommendation_submission": review_row.get("recommendation_submission"),
                        "applicant_document_item": review_row.get("applicant_document_item"),
                        "recommender_name": review_row.get("recommender_name"),
                        "template_name": review_row.get("template_name"),
                        "submitted_on": review_row.get("submitted_on"),
                    }

        for applicant_name, rows in review_rows_by_applicant.items():
            rows.sort(
                key=lambda row: (
                    _sort_datetime_value(row.get("submitted_on")),
                    _sort_datetime_value(row.get("sent_on")),
                    row.get("recommendation_request") or "",
                ),
                reverse=True,
            )
            latest_submitted = next((row.get("submitted_on") for row in rows if row.get("submitted_on")), None)
            latest_submitted_on_by_applicant[applicant_name] = latest_submitted

    status_by_applicant: dict[str, dict] = {}
    for applicant_name in applicant_names:
        template_rows = templates_by_applicant.get(applicant_name) or []
        required_total = 0
        received_total = 0
        requested_total = 0
        missing: list[str] = []
        aggregate_rows: list[dict] = []

        for template_row in template_rows:
            template_name = (template_row.get("name") or "").strip()
            template_label = (template_row.get("template_name") or template_name or "").strip()
            minimum_required = max(0, cint(template_row.get("minimum_required") or 0))
            template_statuses = grouped_statuses_by_applicant.get(applicant_name, {}).get(template_name, [])
            submitted_count = len([status for status in template_statuses if status == "Submitted"])
            requested_count = len([status for status in template_statuses if status in {"Sent", "Opened", "Submitted"}])

            required_total += minimum_required
            received_total += submitted_count
            requested_total += requested_count
            if minimum_required > submitted_count:
                missing.append(template_label or template_name)

            aggregate_rows.append(
                {
                    "recommendation_template": template_name or None,
                    "template_name": template_label or None,
                    "minimum_required": minimum_required,
                    "submitted_count": submitted_count,
                    "requested_count": requested_count,
                }
            )

        summary = _summary_from_rows(
            [
                {"request_status": status}
                for template_statuses in grouped_statuses_by_applicant.get(applicant_name, {}).values()
                for status in template_statuses
            ],
            required_total=required_total,
            received_total=received_total,
        )
        payload = {
            "ok": not missing,
            "required_total": required_total,
            "received_total": received_total,
            "requested_total": requested_total,
            "missing": missing,
            "rows": aggregate_rows,
            "state": summary.get("state"),
            "counts": status_counts_by_applicant.get(applicant_name)
            or {status: 0 for status in sorted(REQUEST_STATUS_ALL)},
        }
        if include_confidential:
            payload.update(
                {
                    "review_rows": review_rows_by_applicant.get(applicant_name) or [],
                    "pending_review_count": pending_review_count_by_applicant.get(applicant_name, 0),
                    "first_pending_review": first_pending_review_by_applicant.get(applicant_name),
                    "latest_submitted_on": latest_submitted_on_by_applicant.get(applicant_name),
                }
            )
        status_by_applicant[applicant_name] = payload

    return status_by_applicant


@frappe.whitelist()
def list_recommendation_templates(*, student_applicant: str | None = None):
    ensure_admissions_permission()
    _require_feature_ready()

    student_applicant = (student_applicant or "").strip()
    if not student_applicant:
        frappe.throw(_("student_applicant is required."))

    applicant_row, org_scope, school_scope = _request_scope_ancestors(student_applicant)
    rows = frappe.get_all(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        filters={"is_active": 1},
        fields=[
            "name",
            "template_name",
            "organization",
            "school",
            "minimum_required",
            "maximum_allowed",
            "allow_file_upload",
            "file_upload_required",
            "otp_enforced",
            "applicant_can_view_status",
            "target_document_type",
        ],
        order_by="template_name asc",
    )

    payload = []
    for row in rows:
        if not _template_in_scope(template_row=row, org_scope=org_scope, school_scope=school_scope):
            continue
        payload.append(
            {
                "name": row.get("name"),
                "template_name": row.get("template_name") or row.get("name"),
                "minimum_required": max(0, cint(row.get("minimum_required") or 0)),
                "maximum_allowed": max(1, cint(row.get("maximum_allowed") or 1)),
                "allow_file_upload": bool(cint(row.get("allow_file_upload"))),
                "file_upload_required": bool(cint(row.get("file_upload_required"))),
                "otp_enforced": bool(cint(row.get("otp_enforced"))),
                "applicant_can_view_status": bool(cint(row.get("applicant_can_view_status"))),
                "target_document_type": row.get("target_document_type"),
                "organization": applicant_row.get("organization"),
                "school": applicant_row.get("school"),
            }
        )

    return {"templates": payload}


@frappe.whitelist()
def create_recommendation_request(payload=None, **kwargs):
    user = ensure_admissions_permission()
    _require_feature_ready()
    data = _normalize_payload(payload, kwargs)

    student_applicant = (data.get("student_applicant") or "").strip()
    template_name = (data.get("recommendation_template") or "").strip()
    recommender_name = (data.get("recommender_name") or "").strip()
    recommender_email = normalize_email_value(data.get("recommender_email"))
    relationship = (data.get("recommender_relationship") or "").strip() or None
    item_label = (data.get("item_label") or "").strip() or None
    send_email = _as_bool(data.get("send_email", 1))
    client_request_id = (data.get("client_request_id") or "").strip() or None
    expires_in_days = max(1, cint(data.get("expires_in_days") or TOKEN_DEFAULT_EXPIRY_DAYS))
    expires_in_days = min(expires_in_days, TOKEN_MAX_EXPIRY_DAYS)

    if not student_applicant:
        frappe.throw(_("student_applicant is required."))
    if not template_name:
        frappe.throw(_("recommendation_template is required."))
    if not recommender_name:
        frappe.throw(_("recommender_name is required."))
    if not recommender_email:
        frappe.throw(_("recommender_email is required."))

    idempotency_key = None
    cache = frappe.cache()
    if client_request_id:
        idempotency_key = f"ifitwala_ed:recommendation:create:{user}:{student_applicant}:{template_name}:{recommender_email}:{client_request_id}"
        existing = cache.get_value(idempotency_key)
        if existing:
            parsed = frappe.parse_json(existing)
            if isinstance(parsed, dict):
                return {**parsed, "status": "already_processed", "idempotent": True}

    lock_key = f"ifitwala_ed:lock:recommendation:create:{student_applicant}:{template_name}:{recommender_email}"
    with cache.lock(lock_key, timeout=15):
        if idempotency_key:
            existing = cache.get_value(idempotency_key)
            if existing:
                parsed = frappe.parse_json(existing)
                if isinstance(parsed, dict):
                    return {**parsed, "status": "already_processed", "idempotent": True}

        applicant_row, template_row = _ensure_template_scope_for_applicant(
            student_applicant=student_applicant,
            template_name=template_name,
        )
        max_allowed = max(1, cint(template_row.get("maximum_allowed") or 1))
        active_or_submitted_count = frappe.db.count(
            RECOMMENDATION_REQUEST_DOCTYPE,
            {
                "student_applicant": student_applicant,
                "recommendation_template": template_name,
                "request_status": ["in", ["Sent", "Opened", "Submitted"]],
            },
        )
        if active_or_submitted_count >= max_allowed:
            frappe.throw(
                _("Maximum recommendation requests reached for template {template_name}.").format(
                    template_name=template_name
                ),
                frappe.ValidationError,
            )

        duplicate_open = frappe.db.exists(
            RECOMMENDATION_REQUEST_DOCTYPE,
            {
                "student_applicant": student_applicant,
                "recommendation_template": template_name,
                "recommender_email": recommender_email,
                "request_status": ["in", ["Sent", "Opened"]],
            },
        )
        if duplicate_open:
            frappe.throw(
                _("An open recommendation request already exists for this recommender email."),
                frappe.ValidationError,
            )

        snapshot = _template_snapshot(template_name)
        token = frappe.generate_hash(length=48)
        token_hash = _token_hash(token)
        token_hint = token[-8:]
        item_key = _new_item_key(student_applicant)
        resolved_item_label = item_label or _("Recommendation - {recommender_name}").format(
            recommender_name=recommender_name
        )
        expires_on = add_to_date(now_datetime(), days=expires_in_days, as_datetime=True)

        applicant_document, applicant_document_item = _ensure_document_item_slot(
            student_applicant=student_applicant,
            target_document_type=template_row.get("target_document_type"),
            item_key=item_key,
            item_label=resolved_item_label,
        )

        request_doc = frappe.get_doc(
            {
                "doctype": RECOMMENDATION_REQUEST_DOCTYPE,
                "student_applicant": student_applicant,
                "recommendation_template": template_name,
                "target_document_type": template_row.get("target_document_type"),
                "applicant_document": applicant_document,
                "applicant_document_item": applicant_document_item,
                "item_key": item_key,
                "item_label": resolved_item_label,
                "request_status": "Sent",
                "recommender_name": recommender_name,
                "recommender_email": recommender_email,
                "recommender_relationship": relationship,
                "expires_on": expires_on,
                "sent_on": now_datetime(),
                "resend_count": 0,
                "token_hash": token_hash,
                "token_hint": token_hint,
                "otp_enforced": 1 if cint(template_row.get("otp_enforced")) else 0,
                "template_snapshot_json": frappe.as_json(snapshot),
            }
        )
        request_doc.insert(ignore_permissions=True)

        intake_url = _intake_url(token)
        email_sent = False
        if send_email:
            email_sent = _send_recommendation_request_email(
                request_row={"recommender_email": recommender_email, "expires_on": expires_on},
                intake_url=intake_url,
                is_resend=False,
            )

        applicant = frappe.get_doc("Student Applicant", applicant_row.get("name"))
        applicant.add_comment(
            "Comment",
            text=_("Recommendation request created for {recommender_email} by {actor}.").format(
                recommender_email=frappe.bold(recommender_email),
                actor=frappe.bold(frappe.session.user),
            ),
        )

        result = {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "recommendation_request": request_doc.name,
            "student_applicant": student_applicant,
            "template": template_name,
            "recommender_name": recommender_name,
            "recommender_email": recommender_email,
            "expires_on": request_doc.expires_on,
            "request_status": request_doc.request_status,
            "item_key": request_doc.item_key,
            "item_label": request_doc.item_label,
            "intake_url": intake_url,
            "email_sent": email_sent,
        }
        if idempotency_key:
            cache.set_value(idempotency_key, frappe.as_json(result), expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return result


@frappe.whitelist()
def resend_recommendation_request(
    *,
    recommendation_request: str | None = None,
    expires_in_days: int | None = None,
):
    ensure_admissions_permission()
    _require_feature_ready()

    request_name = (recommendation_request or "").strip()
    if not request_name:
        frappe.throw(_("recommendation_request is required."))

    doc = frappe.get_doc(RECOMMENDATION_REQUEST_DOCTYPE, request_name)
    status = (doc.request_status or "").strip()
    if status in {"Submitted", "Revoked"}:
        frappe.throw(_("Only open recommendation requests can be re-sent."))

    if expires_in_days is not None:
        ttl = max(1, min(cint(expires_in_days), TOKEN_MAX_EXPIRY_DAYS))
    else:
        ttl = TOKEN_DEFAULT_EXPIRY_DAYS

    token = frappe.generate_hash(length=48)
    doc.token_hash = _token_hash(token)
    doc.token_hint = token[-8:]
    doc.request_status = "Sent"
    doc.sent_on = now_datetime()
    doc.resend_count = max(0, cint(doc.resend_count or 0)) + 1
    doc.expires_on = add_to_date(now_datetime(), days=ttl, as_datetime=True)
    doc.otp_code_hash = None
    doc.otp_expires_on = None
    doc.otp_verified_on = None
    doc.otp_failed_attempts = 0
    doc.save(ignore_permissions=True)

    intake_url = _intake_url(token)
    email_sent = _send_recommendation_request_email(
        request_row={"recommender_email": doc.recommender_email, "expires_on": doc.expires_on},
        intake_url=intake_url,
        is_resend=True,
    )

    applicant = frappe.get_doc("Student Applicant", doc.student_applicant)
    applicant.add_comment(
        "Comment",
        text=_("Recommendation request re-sent for {recommender_email} by {actor}.").format(
            recommender_email=frappe.bold(doc.recommender_email),
            actor=frappe.bold(frappe.session.user),
        ),
    )

    return {
        "ok": True,
        "recommendation_request": doc.name,
        "request_status": doc.request_status,
        "expires_on": doc.expires_on,
        "intake_url": intake_url,
        "email_sent": email_sent,
    }


@frappe.whitelist()
def revoke_recommendation_request(*, recommendation_request: str | None = None):
    ensure_admissions_permission()
    _require_feature_ready()

    request_name = (recommendation_request or "").strip()
    if not request_name:
        frappe.throw(_("recommendation_request is required."))

    doc = frappe.get_doc(RECOMMENDATION_REQUEST_DOCTYPE, request_name)
    if (doc.request_status or "").strip() == "Submitted":
        frappe.throw(_("Submitted recommendation requests cannot be revoked."))
    if (doc.request_status or "").strip() == "Revoked":
        return {"ok": True, "recommendation_request": doc.name, "request_status": "Revoked", "idempotent": True}

    doc.request_status = "Revoked"
    doc.consumed_on = now_datetime()
    doc.otp_code_hash = None
    doc.otp_expires_on = None
    doc.otp_verified_on = None
    doc.save(ignore_permissions=True)

    applicant = frappe.get_doc("Student Applicant", doc.student_applicant)
    applicant.add_comment(
        "Comment",
        text=_("Recommendation request revoked for {recommender_email} by {actor}.").format(
            recommender_email=frappe.bold(doc.recommender_email),
            actor=frappe.bold(frappe.session.user),
        ),
    )

    return {"ok": True, "recommendation_request": doc.name, "request_status": doc.request_status}


@frappe.whitelist()
def list_recommendation_requests(*, student_applicant: str | None = None):
    _require_feature_ready()
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    applicant_mode = ADMISSIONS_APPLICANT_ROLE in roles and not is_admissions_file_staff_user(user)

    target_student_applicant = (student_applicant or "").strip()
    if applicant_mode:
        applicant_row = _applicant_for_user(user)
        if target_student_applicant and target_student_applicant != applicant_row.get("name"):
            frappe.throw(_("You do not have permission to access this Applicant."), frappe.PermissionError)
        target_student_applicant = applicant_row.get("name")
    else:
        if target_student_applicant:
            _require_staff_recommendation_access(student_applicant=target_student_applicant, user=user)
        else:
            ensure_admissions_permission()

    if target_student_applicant:
        _refresh_expired_requests(student_applicant=target_student_applicant)

    filters = {}
    if target_student_applicant:
        filters["student_applicant"] = target_student_applicant

    rows = frappe.get_all(
        RECOMMENDATION_REQUEST_DOCTYPE,
        filters=filters,
        fields=[
            "name",
            "student_applicant",
            "recommendation_template",
            "request_status",
            "recommender_name",
            "recommender_email",
            "recommender_relationship",
            "expires_on",
            "sent_on",
            "opened_on",
            "consumed_on",
            "resend_count",
            "submission",
        ],
        order_by="modified desc",
    )

    template_names = [row.get("recommendation_template") for row in rows if row.get("recommendation_template")]
    template_map = {}
    if template_names:
        template_rows = frappe.get_all(
            RECOMMENDATION_TEMPLATE_DOCTYPE,
            filters={"name": ["in", template_names]},
            fields=["name", "template_name", "minimum_required", "applicant_can_view_status"],
        )
        template_map = {row.get("name"): row for row in template_rows if row.get("name")}

    payload = []
    for row in rows:
        template_row = template_map.get(row.get("recommendation_template")) or {}
        if applicant_mode and not cint(template_row.get("applicant_can_view_status")):
            continue
        entry = {
            "name": row.get("name"),
            "student_applicant": row.get("student_applicant"),
            "recommendation_template": row.get("recommendation_template"),
            "template_name": template_row.get("template_name") or row.get("recommendation_template"),
            "request_status": row.get("request_status"),
            "expires_on": row.get("expires_on"),
            "sent_on": row.get("sent_on"),
            "opened_on": row.get("opened_on"),
            "consumed_on": row.get("consumed_on"),
            "resend_count": cint(row.get("resend_count") or 0),
            "submission": row.get("submission"),
        }
        if not applicant_mode:
            entry.update(
                {
                    "recommender_name": row.get("recommender_name"),
                    "recommender_email": row.get("recommender_email"),
                    "recommender_relationship": row.get("recommender_relationship"),
                }
            )
        payload.append(entry)

    required_by_template = {}
    received_total = 0
    for row in payload:
        template_name = row.get("recommendation_template")
        template_row = template_map.get(template_name) or {}
        if template_name:
            required_by_template[template_name] = max(0, cint(template_row.get("minimum_required") or 0))
        if (row.get("request_status") or "").strip() == "Submitted":
            received_total += 1

    required_total = sum(required_by_template.values())

    summary = _summary_from_rows(payload, required_total=required_total, received_total=received_total)
    response = {
        "requests": payload,
        "summary": summary,
    }
    if not applicant_mode and target_student_applicant:
        confidential_summary = get_recommendation_status_for_applicant(
            student_applicant=target_student_applicant,
            include_confidential=True,
        )
        response["review_rows"] = confidential_summary.get("review_rows") or []
    return response


@frappe.whitelist()
def get_recommendation_request_summary(*, student_applicant: str | None = None):
    return list_recommendation_requests(student_applicant=student_applicant)


def get_recommendation_status_for_applicant(
    *,
    student_applicant: str,
    include_confidential: bool = False,
) -> dict:
    student_applicant = (student_applicant or "").strip()
    if not student_applicant:
        return _default_recommendation_status_payload(include_confidential=include_confidential)

    applicant_row = frappe.db.get_value(
        "Student Applicant",
        student_applicant,
        ["name", "organization", "school"],
        as_dict=True,
    )
    if not applicant_row:
        return _default_recommendation_status_payload(include_confidential=include_confidential)

    _refresh_expired_requests(student_applicant=student_applicant)
    batch_payload = get_recommendation_status_batch_for_applicants(
        applicant_rows=[applicant_row],
        include_confidential=include_confidential,
    )
    return batch_payload.get(student_applicant) or _default_recommendation_status_payload(
        include_confidential=include_confidential
    )


@frappe.whitelist()
def get_recommendation_review_payload(
    *,
    student_applicant: str | None = None,
    recommendation_request: str | None = None,
    recommendation_submission: str | None = None,
    applicant_document_item: str | None = None,
):
    _require_feature_ready()

    applicant_name = (student_applicant or "").strip()
    request_name = (recommendation_request or "").strip()
    submission_name = (recommendation_submission or "").strip()
    item_name = (applicant_document_item or "").strip()

    anchors_used = sum(bool(value) for value in (request_name, submission_name, item_name))
    if anchors_used != 1:
        frappe.throw(_("Provide exactly one recommendation reference."), frappe.ValidationError)

    request_filters: dict[str, object]
    if request_name:
        request_filters = {"name": request_name}
    elif submission_name:
        request_filters = {"submission": submission_name}
    else:
        request_filters = {"applicant_document_item": item_name}

    request_row = frappe.db.get_value(
        RECOMMENDATION_REQUEST_DOCTYPE,
        request_filters,
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
            "sent_on",
            "opened_on",
            "consumed_on",
            "submission",
            "template_snapshot_json",
        ],
        as_dict=True,
    )
    if not request_row:
        frappe.throw(_("Recommendation review reference was not found."), frappe.DoesNotExistError)

    resolved_applicant = (request_row.get("student_applicant") or "").strip()
    if applicant_name and applicant_name != resolved_applicant:
        frappe.throw(_("Recommendation does not belong to this Applicant."), frappe.PermissionError)

    _require_staff_recommendation_access(student_applicant=resolved_applicant)

    request_status = (request_row.get("request_status") or "").strip()
    if request_status != "Submitted" or not (request_row.get("submission") or "").strip():
        frappe.throw(_("This recommendation has not been submitted yet."), frappe.ValidationError)

    submission_row = frappe.db.get_value(
        RECOMMENDATION_SUBMISSION_DOCTYPE,
        (request_row.get("submission") or "").strip(),
        [
            "name",
            "recommendation_request",
            "student_applicant",
            "recommendation_template",
            "applicant_document",
            "applicant_document_item",
            "recommender_name",
            "recommender_email",
            "answers_json",
            "attestation_confirmed",
            "has_file",
            "submitted_on",
        ],
        as_dict=True,
    )
    if not submission_row:
        frappe.throw(_("Recommendation submission payload was not found."), frappe.DoesNotExistError)

    applicant_document_item_name = (submission_row.get("applicant_document_item") or "").strip() or (
        request_row.get("applicant_document_item") or ""
    ).strip()
    item_row = {}
    if applicant_document_item_name:
        item_row = (
            frappe.db.get_value(
                "Applicant Document Item",
                applicant_document_item_name,
                ["name", "review_status", "reviewed_by", "reviewed_on"],
                as_dict=True,
            )
            or {}
        )

    latest_attachment = {}
    if applicant_document_item_name:
        latest_drive_file = get_current_drive_files_for_attachments(
            attached_doctype="Applicant Document Item",
            attached_names=[applicant_document_item_name],
            fields=[
                "name",
                "attached_name",
                "file",
                "canonical_ref",
                "display_name",
                "preview_status",
                "current_version",
                "creation",
            ],
            statuses=("active", "processing", "blocked"),
        )
        latest_drive_file = latest_drive_file[0] if latest_drive_file else None
        latest_attachment = _serialize_recommendation_attachment(
            student_applicant=resolved_applicant,
            latest_drive_file=latest_drive_file,
            thumbnail_ready_map=get_drive_file_thumbnail_ready_map(
                [_text(latest_drive_file.get("name"))] if latest_drive_file else []
            ),
            version_mime_map=_load_drive_version_mime_map(
                [_text(latest_drive_file.get("current_version"))] if latest_drive_file else []
            ),
        )

    template_name = (request_row.get("recommendation_template") or "").strip()
    template_meta = (
        frappe.db.get_value(
            RECOMMENDATION_TEMPLATE_DOCTYPE,
            template_name,
            ["name", "template_name"],
            as_dict=True,
        )
        or {}
    )
    snapshot = _parse_snapshot(request_row.get("template_snapshot_json"), template_name)

    return {
        "ok": True,
        "recommendation": {
            "student_applicant": resolved_applicant,
            "recommendation_request": (request_row.get("name") or "").strip(),
            "recommendation_submission": (submission_row.get("name") or "").strip(),
            "recommendation_template": template_name or None,
            "template_name": (template_meta.get("template_name") or template_name or "").strip() or None,
            "target_document_type": (request_row.get("target_document_type") or "").strip() or None,
            "applicant_document": (
                (submission_row.get("applicant_document") or "").strip()
                or (request_row.get("applicant_document") or "").strip()
                or None
            ),
            "applicant_document_item": applicant_document_item_name or None,
            "item_key": (request_row.get("item_key") or "").strip() or None,
            "item_label": (request_row.get("item_label") or "").strip() or None,
            "request_status": request_status,
            "review_status": (item_row.get("review_status") or "").strip() or "Pending",
            "reviewed_by": (item_row.get("reviewed_by") or "").strip() or None,
            "reviewed_on": item_row.get("reviewed_on"),
            "recommender_name": (request_row.get("recommender_name") or "").strip() or None,
            "recommender_email": (request_row.get("recommender_email") or "").strip() or None,
            "recommender_relationship": (request_row.get("recommender_relationship") or "").strip() or None,
            "sent_on": request_row.get("sent_on"),
            "opened_on": request_row.get("opened_on"),
            "submitted_on": submission_row.get("submitted_on") or request_row.get("consumed_on"),
            "expires_on": request_row.get("expires_on"),
            "has_file": bool(cint(submission_row.get("has_file"))),
            "attestation_confirmed": bool(cint(submission_row.get("attestation_confirmed"))),
            "file_name": latest_attachment.get("file_name"),
            "open_url": latest_attachment.get("open_url"),
            "preview_url": latest_attachment.get("preview_url"),
            "thumbnail_url": latest_attachment.get("thumbnail_url"),
            "preview_status": latest_attachment.get("preview_status"),
            "drive_file_id": latest_attachment.get("drive_file_id"),
            "canonical_ref": latest_attachment.get("canonical_ref"),
            "attachment_preview": latest_attachment.get("attachment_preview"),
            "answers": _build_recommendation_answer_rows(snapshot, submission_row.get("answers_json")),
            "can_review": bool(
                applicant_document_item_name
                and (item_row.get("review_status") or "").strip() in {"", "Pending", "Needs Follow-Up", "Rejected"}
            ),
            "needs_review": bool(
                applicant_document_item_name and (item_row.get("review_status") or "").strip() in {"", "Pending"}
            ),
        },
    }


@frappe.whitelist(allow_guest=True)
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


@frappe.whitelist(allow_guest=True)
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


@frappe.whitelist(allow_guest=True)
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


@frappe.whitelist(allow_guest=True)
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
        has_file_in_request = bool(data.get("content")) or bool(request_files and request_files.get("file"))
        allow_file_upload = bool(template_meta.get("allow_file_upload"))
        file_upload_required = bool(template_meta.get("file_upload_required"))
        if has_file_in_request and not allow_file_upload:
            frappe.throw(_("This recommendation does not allow file uploads."), frappe.ValidationError)
        if file_upload_required and not has_file_in_request:
            frappe.throw(_("A file upload is required for this recommendation."), frappe.ValidationError)

        upload_result = None
        if has_file_in_request:
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
