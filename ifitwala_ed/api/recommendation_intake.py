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
    is_applicant_document_type_in_scope,
    normalize_email_value,
)

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
        frappe.throw(_("Invalid Student Applicant: {0}.").format(student_applicant))

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
        frappe.throw(_("Invalid Recommendation Template: {0}.").format(template_name))
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
    message = _("You have received a {0}. Use this secure link to submit the recommendation before {1}: {2}").format(
        status_label,
        request_row.get("expires_on"),
        intake_url,
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
                frappe.throw(_("Required field is missing: {0}.").format(label), frappe.ValidationError)
        else:
            value = "" if raw_value is None else str(raw_value).strip()
            if required and not value:
                frappe.throw(_("Required field is missing: {0}.").format(label), frappe.ValidationError)
            if field_type == "Select" and value and options and value not in options:
                frappe.throw(_("Invalid option for {0}.").format(label), frappe.ValidationError)

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


def _applicant_for_user(user: str) -> dict:
    rows = frappe.get_all(
        "Student Applicant",
        filters={"applicant_user": user},
        fields=["name", "organization", "school"],
        limit_page_length=2,
    )
    if not rows:
        frappe.throw(_("Admissions access is not linked to any Applicant."), frappe.PermissionError)
    if len(rows) > 1:
        frappe.throw(_("Admissions access is linked to multiple Applicants."), frappe.PermissionError)
    return rows[0]


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
                _("Maximum recommendation requests reached for template {0}.").format(template_name),
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
        resolved_item_label = item_label or _("Recommendation - {0}").format(recommender_name)
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
            text=_("Recommendation request created for {0} by {1}.").format(
                frappe.bold(recommender_email),
                frappe.bold(frappe.session.user),
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
        text=_("Recommendation request re-sent for {0} by {1}.").format(
            frappe.bold(doc.recommender_email),
            frappe.bold(frappe.session.user),
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
        text=_("Recommendation request revoked for {0} by {1}.").format(
            frappe.bold(doc.recommender_email),
            frappe.bold(frappe.session.user),
        ),
    )

    return {"ok": True, "recommendation_request": doc.name, "request_status": doc.request_status}


@frappe.whitelist()
def list_recommendation_requests(*, student_applicant: str | None = None):
    _require_feature_ready()
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    applicant_mode = ADMISSIONS_APPLICANT_ROLE in roles and not (roles & {"Admission Manager", "Admission Officer"})

    target_student_applicant = (student_applicant or "").strip()
    if applicant_mode:
        applicant_row = _applicant_for_user(user)
        if target_student_applicant and target_student_applicant != applicant_row.get("name"):
            frappe.throw(_("You do not have permission to access this Applicant."), frappe.PermissionError)
        target_student_applicant = applicant_row.get("name")
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
    return {
        "requests": payload,
        "summary": summary,
    }


@frappe.whitelist()
def get_recommendation_request_summary(*, student_applicant: str | None = None):
    return list_recommendation_requests(student_applicant=student_applicant)


def get_recommendation_status_for_applicant(
    *,
    student_applicant: str,
    include_confidential: bool = False,
) -> dict:
    if not _feature_ready():
        return {
            "ok": True,
            "required_total": 0,
            "received_total": 0,
            "requested_total": 0,
            "missing": [],
            "rows": [],
            "state": "optional",
            "counts": {status: 0 for status in sorted(REQUEST_STATUS_ALL)},
        }

    student_applicant = (student_applicant or "").strip()
    if not student_applicant:
        return {
            "ok": True,
            "required_total": 0,
            "received_total": 0,
            "requested_total": 0,
            "missing": [],
            "rows": [],
            "state": "optional",
            "counts": {status: 0 for status in sorted(REQUEST_STATUS_ALL)},
        }

    _refresh_expired_requests(student_applicant=student_applicant)
    applicant_row, org_scope, school_scope = _request_scope_ancestors(student_applicant)
    templates = frappe.get_all(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        filters={"is_active": 1},
        fields=[
            "name",
            "template_name",
            "minimum_required",
            "applicant_can_view_status",
            "organization",
            "school",
        ],
    )
    template_rows = []
    for row in templates:
        if not _template_in_scope(template_row=row, org_scope=org_scope, school_scope=school_scope):
            continue
        if not include_confidential and not cint(row.get("applicant_can_view_status")):
            continue
        template_rows.append(row)

    if not template_rows:
        return {
            "ok": True,
            "required_total": 0,
            "received_total": 0,
            "requested_total": 0,
            "missing": [],
            "rows": [],
            "state": "optional",
            "counts": {status: 0 for status in sorted(REQUEST_STATUS_ALL)},
        }

    template_names = [row.get("name") for row in template_rows if row.get("name")]
    request_rows = frappe.get_all(
        RECOMMENDATION_REQUEST_DOCTYPE,
        filters={
            "student_applicant": applicant_row.get("name"),
            "recommendation_template": ["in", template_names],
        },
        fields=["recommendation_template", "request_status"],
    )
    grouped = {}
    counts = {status: 0 for status in sorted(REQUEST_STATUS_ALL)}
    for request_row in request_rows:
        template_name = request_row.get("recommendation_template")
        if not template_name:
            continue
        status = (request_row.get("request_status") or "").strip()
        grouped.setdefault(template_name, []).append(status)
        if status in counts:
            counts[status] += 1

    rows = []
    missing = []
    required_total = 0
    received_total = 0
    requested_total = 0
    for template in template_rows:
        template_name = template.get("name")
        statuses = grouped.get(template_name, [])
        minimum_required = max(0, cint(template.get("minimum_required") or 0))
        submitted_count = len([status for status in statuses if status == "Submitted"])
        active_count = len([status for status in statuses if status in {"Sent", "Opened", "Submitted"}])

        required_total += minimum_required
        received_total += submitted_count
        requested_total += active_count

        if minimum_required > submitted_count:
            missing.append(template.get("template_name") or template_name)

        rows.append(
            {
                "recommendation_template": template_name,
                "template_name": template.get("template_name") or template_name,
                "minimum_required": minimum_required,
                "submitted_count": submitted_count,
                "requested_count": active_count,
            }
        )

    summary = _summary_from_rows(
        [{"request_status": status} for status in [status for group in grouped.values() for status in group]],
        required_total=required_total,
        received_total=received_total,
    )
    return {
        "ok": not missing,
        "required_total": required_total,
        "received_total": received_total,
        "requested_total": requested_total,
        "missing": missing,
        "rows": rows,
        "state": summary.get("state"),
        "counts": counts,
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
            message=_("Your verification code is {0}. It expires in {1} minutes.").format(code, OTP_TTL_MINUTES),
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

        has_file_in_request = bool(data.get("content")) or bool(
            getattr(frappe.request, "files", None) and frappe.request.files.get("file")
        )
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
                "source_ip": frappe.local.request_ip if frappe.request else None,
                "user_agent": (frappe.request.headers.get("User-Agent") if frappe.request else None),
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
            text=_("Recommendation submitted for request {0}.").format(frappe.bold(request_doc.name)),
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
