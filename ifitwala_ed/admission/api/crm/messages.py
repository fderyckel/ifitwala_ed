# ifitwala_ed/admission/api/crm/messages.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import ensure_admissions_crm_permission
from ifitwala_ed.admission.api.crm.conversations import _resolve_or_create_conversation
from ifitwala_ed.admission.api.crm.idempotency import (
    IDEMPOTENCY_TTL_SECONDS,
    _cache,
    _idempotency_key,
    _lock_key,
)
from ifitwala_ed.admission.api.crm.summaries import _conversation_summary, _message_summary


def _log_admission_message(
    *,
    user: str,
    conversation: str | None,
    inquiry: str | None,
    student_applicant: str | None,
    external_identity: str | None,
    channel_account: str | None,
    organization: str | None,
    school: str | None,
    assigned_to: str | None,
    direction: str | None,
    body: str | None,
    message_type: str | None,
    delivery_status: str | None,
    message_at: str | None,
    external_message_id: str | None,
    external_conversation_id: str | None,
    dedupe_key: str | None,
    provider_payload_json: str | None,
    media_provider_id: str | None,
    media_mime_type: str | None,
    media_file_name: str | None,
    media_size: int | None,
    media_status: str | None,
) -> dict:
    direction_value = clean(direction) or "Inbound"
    if direction_value not in {"Inbound", "Outbound", "System"}:
        frappe.throw(_("Invalid message direction: {direction}.").format(direction=direction_value))

    conversation_doc = _resolve_or_create_conversation(
        user=user,
        conversation=conversation,
        inquiry=inquiry,
        student_applicant=student_applicant,
        external_identity=external_identity,
        channel_account=channel_account,
        organization=organization,
        school=school,
        assigned_to=assigned_to,
    )

    resolved_dedupe_key = clean(dedupe_key)
    if not resolved_dedupe_key and clean(channel_account) and clean(external_message_id):
        resolved_dedupe_key = f"{clean(channel_account)}:{clean(external_message_id)}"
    if resolved_dedupe_key:
        existing_message = frappe.db.get_value("Admission Message", {"dedupe_key": resolved_dedupe_key}, "name")
        if existing_message:
            return {
                "ok": True,
                "deduped": True,
                "conversation": _conversation_summary(conversation_doc.name),
                "message": _message_summary(existing_message),
            }

    message_doc = frappe.get_doc(
        {
            "doctype": "Admission Message",
            "conversation": conversation_doc.name,
            "direction": direction_value,
            "message_type": clean(message_type) or "Text",
            "body": body,
            "delivery_status": clean(delivery_status),
            "message_at": clean(message_at),
            "channel_account": clean(channel_account),
            "external_identity": clean(external_identity),
            "external_message_id": clean(external_message_id),
            "external_conversation_id": clean(external_conversation_id),
            "dedupe_key": resolved_dedupe_key or None,
            "provider_payload_json": provider_payload_json,
            "media_provider_id": clean(media_provider_id),
            "media_mime_type": clean(media_mime_type),
            "media_file_name": clean(media_file_name),
            "media_size": media_size,
            "media_status": clean(media_status) or "None",
        }
    )
    message_doc.insert(ignore_permissions=True)

    return {
        "ok": True,
        "deduped": False,
        "conversation": _conversation_summary(conversation_doc.name),
        "message": _message_summary(message_doc.name),
    }


def log_admission_message_impl(
    *,
    conversation: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    external_identity: str | None = None,
    channel_account: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    assigned_to: str | None = None,
    direction: str | None = "Inbound",
    body: str | None = None,
    message_type: str | None = "Text",
    delivery_status: str | None = None,
    message_at: str | None = None,
    external_message_id: str | None = None,
    external_conversation_id: str | None = None,
    dedupe_key: str | None = None,
    provider_payload_json: str | None = None,
    media_provider_id: str | None = None,
    media_mime_type: str | None = None,
    media_file_name: str | None = None,
    media_size: int | None = None,
    media_status: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    request_id = clean(client_request_id)
    target = clean(conversation) or clean(student_applicant) or clean(inquiry) or clean(external_identity) or "new"

    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key("log_message", user, target, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key("log_message", user, target), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        response = _log_admission_message(
            user=user,
            conversation=conversation,
            inquiry=inquiry,
            student_applicant=student_applicant,
            external_identity=external_identity,
            channel_account=channel_account,
            organization=organization,
            school=school,
            assigned_to=assigned_to,
            direction=direction,
            body=body,
            message_type=message_type,
            delivery_status=delivery_status,
            message_at=message_at,
            external_message_id=external_message_id,
            external_conversation_id=external_conversation_id,
            dedupe_key=dedupe_key,
            provider_payload_json=provider_payload_json,
            media_provider_id=media_provider_id,
            media_mime_type=media_mime_type,
            media_file_name=media_file_name,
            media_size=media_size,
            media_status=media_status,
        )
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return response
