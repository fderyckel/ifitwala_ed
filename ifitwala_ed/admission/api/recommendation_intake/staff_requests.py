# ifitwala_ed/admission/api/recommendation_intake/staff_requests.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime

from ifitwala_ed.admission.admission_utils import (
    ensure_admissions_permission,
    is_admissions_file_staff_user,
    normalize_email_value,
)
from ifitwala_ed.admission.api.recommendation_intake.access import (
    _applicant_for_user,
    _intake_url,
    _require_feature_ready,
    _require_staff_recommendation_access,
    _token_hash,
)
from ifitwala_ed.admission.api.recommendation_intake.constants import (
    ADMISSIONS_APPLICANT_ROLE,
    IDEMPOTENCY_TTL_SECONDS,
    RECOMMENDATION_REQUEST_DOCTYPE,
    RECOMMENDATION_TEMPLATE_DOCTYPE,
    TOKEN_DEFAULT_EXPIRY_DAYS,
    TOKEN_MAX_EXPIRY_DAYS,
)
from ifitwala_ed.admission.api.recommendation_intake.document_integration import (
    _ensure_document_item_slot,
    _new_item_key,
)
from ifitwala_ed.admission.api.recommendation_intake.dto import _as_bool, _normalize_payload
from ifitwala_ed.admission.api.recommendation_intake.status import (
    _refresh_expired_requests,
    _summary_from_rows,
    get_recommendation_status_for_applicant,
)
from ifitwala_ed.admission.api.recommendation_intake.templates import (
    _ensure_template_scope_for_applicant,
    _template_snapshot,
)


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


def get_recommendation_request_summary(*, student_applicant: str | None = None):
    return list_recommendation_requests(student_applicant=student_applicant)
