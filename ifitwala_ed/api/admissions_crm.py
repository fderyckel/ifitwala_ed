from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean, get_channel_account_context
from ifitwala_ed.admission.admissions_crm_permissions import (
    doc_is_in_admissions_crm_scope,
    ensure_admissions_crm_permission,
)

IDEMPOTENCY_TTL_SECONDS = 60 * 10


def _cache():
    return frappe.cache()


def _cache_key(*parts: str) -> str:
    cleaned = [str(part or "").strip() for part in parts if str(part or "").strip()]
    return "ifitwala_ed:admissions_crm:" + ":".join(cleaned)


def _lock_key(*parts: str) -> str:
    return _cache_key("lock", *parts)


def _idempotency_key(*parts: str) -> str:
    return _cache_key("idempotency", *parts)


def _require_doc_read(user: str, doctype: str, name: str | None):
    docname = clean(name)
    if not docname:
        return None
    doc = frappe.get_doc(doctype, docname)
    if not frappe.has_permission(doctype, ptype="read", doc=doc, user=user):
        frappe.throw(_("You do not have permission to use {0} {1}.").format(doctype, docname), frappe.PermissionError)
    return doc


def _assert_scope_allowed(user: str, *, organization: str | None, school: str | None) -> None:
    if doc_is_in_admissions_crm_scope(user=user, organization=organization, school=school):
        return
    frappe.throw(_("You do not have permission for this admissions CRM scope."), frappe.PermissionError)


def _conversation_summary(conversation_name: str) -> dict:
    row = frappe.db.get_value(
        "Admission Conversation",
        conversation_name,
        [
            "name",
            "title",
            "organization",
            "school",
            "assigned_to",
            "status",
            "inquiry",
            "student_applicant",
            "external_identity",
            "channel_account",
            "latest_message_at",
            "latest_inbound_message_at",
            "latest_outbound_message_at",
            "needs_reply",
            "last_message_preview",
            "next_action_on",
            "last_activity_at",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _message_summary(message_name: str) -> dict:
    row = frappe.db.get_value(
        "Admission Message",
        message_name,
        [
            "name",
            "conversation",
            "direction",
            "message_type",
            "delivery_status",
            "message_at",
            "linked_inquiry",
            "linked_student_applicant",
            "media_status",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _activity_summary(activity_name: str) -> dict:
    row = frappe.db.get_value(
        "Admission CRM Activity",
        activity_name,
        [
            "name",
            "conversation",
            "activity_type",
            "outcome",
            "next_action_on",
            "staff_user",
            "activity_at",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _require_conversation_write(user: str, conversation: str):
    conversation_name = clean(conversation)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))
    doc = frappe.get_doc("Admission Conversation", conversation_name)
    if not frappe.has_permission("Admission Conversation", ptype="write", doc=doc, user=user):
        frappe.throw(_("You do not have permission to update this admissions conversation."), frappe.PermissionError)
    return doc


def _apply_identity_defaults(*, external_identity: str | None, values: dict) -> None:
    identity_name = clean(external_identity)
    if not identity_name:
        return

    row = frappe.db.get_value(
        "Admission External Identity",
        identity_name,
        ["channel_account", "linked_inquiry", "linked_student_applicant", "match_status"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Admission External Identity not found: {0}").format(identity_name))

    if not clean(values.get("channel_account")):
        values["channel_account"] = row.get("channel_account")
    if row.get("match_status") == "Confirmed":
        if not clean(values.get("inquiry")):
            values["inquiry"] = row.get("linked_inquiry")
        if not clean(values.get("student_applicant")):
            values["student_applicant"] = row.get("linked_student_applicant")


def _candidate_conversation(values: dict) -> str | None:
    for key in ("student_applicant", "inquiry", "external_identity"):
        value = clean(values.get(key))
        if not value:
            continue
        filters = {key: value, "status": ["!=", "Spam"]}
        channel_account = clean(values.get("channel_account"))
        if channel_account:
            filters["channel_account"] = channel_account
        existing = frappe.db.get_value(
            "Admission Conversation",
            filters,
            "name",
            order_by="modified desc",
        )
        if existing:
            return existing
    return None


def _resolve_or_create_conversation(
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
):
    conversation_name = clean(conversation)
    if conversation_name:
        return _require_conversation_write(user, conversation_name)

    values = {
        "inquiry": clean(inquiry),
        "student_applicant": clean(student_applicant),
        "external_identity": clean(external_identity),
        "channel_account": clean(channel_account),
        "organization": clean(organization),
        "school": clean(school),
        "assigned_to": clean(assigned_to) or user,
    }
    _apply_identity_defaults(external_identity=external_identity, values=values)

    existing = _candidate_conversation(values)
    if existing:
        return _require_conversation_write(user, existing)

    if values.get("inquiry"):
        _require_doc_read(user, "Inquiry", values["inquiry"])
    if values.get("student_applicant"):
        _require_doc_read(user, "Student Applicant", values["student_applicant"])
    if values.get("channel_account"):
        account = get_channel_account_context(values["channel_account"])
        if not clean(values.get("organization")):
            values["organization"] = clean(account.get("organization"))
        if not clean(values.get("school")):
            values["school"] = clean(account.get("school"))

    doc = frappe.get_doc(
        {
            "doctype": "Admission Conversation",
            **values,
        }
    )
    doc.run_method("validate")
    _assert_scope_allowed(user, organization=doc.organization, school=doc.school)
    doc.insert(ignore_permissions=True)
    return doc


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
        frappe.throw(_("Invalid message direction: {0}.").format(direction_value))

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


@frappe.whitelist()
def log_admission_message(
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


@frappe.whitelist()
def record_admission_crm_activity(
    *,
    conversation: str | None = None,
    activity_type: str | None = None,
    outcome: str | None = None,
    note: str | None = None,
    next_action_on: str | None = None,
    activity_at: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    conversation_name = clean(conversation)
    activity_type_value = clean(activity_type)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))
    if not activity_type_value:
        frappe.throw(_("Activity Type is required."))

    request_id = clean(client_request_id)
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key("record_activity", user, conversation_name, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key("record_activity", user, conversation_name), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        _require_conversation_write(user, conversation_name)
        activity_doc = frappe.get_doc(
            {
                "doctype": "Admission CRM Activity",
                "conversation": conversation_name,
                "activity_type": activity_type_value,
                "outcome": outcome,
                "note": note,
                "next_action_on": clean(next_action_on),
                "activity_at": clean(activity_at),
            }
        )
        activity_doc.insert(ignore_permissions=True)
        response = {
            "ok": True,
            "conversation": _conversation_summary(conversation_name),
            "activity": _activity_summary(activity_doc.name),
        }
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return response


@frappe.whitelist()
def link_admission_conversation(
    *,
    conversation: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    external_identity: str | None = None,
    channel_account: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    conversation_name = clean(conversation)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))

    request_id = clean(client_request_id)
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key("link_conversation", user, conversation_name, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key("link_conversation", user, conversation_name), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        doc = _require_conversation_write(user, conversation_name)
        if clean(inquiry):
            _require_doc_read(user, "Inquiry", inquiry)
            doc.inquiry = clean(inquiry)
        if clean(student_applicant):
            _require_doc_read(user, "Student Applicant", student_applicant)
            doc.student_applicant = clean(student_applicant)
        if clean(external_identity):
            identity_doc = _require_doc_read(user, "Admission External Identity", external_identity)
            doc.external_identity = identity_doc.name
        if clean(channel_account):
            account = get_channel_account_context(channel_account)
            _assert_scope_allowed(user, organization=account.get("organization"), school=account.get("school"))
            doc.channel_account = clean(channel_account)

        doc.run_method("validate")
        _assert_scope_allowed(user, organization=doc.organization, school=doc.school)
        doc.save(ignore_permissions=True)
        response = {"ok": True, "conversation": _conversation_summary(doc.name)}
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return response


@frappe.whitelist()
def confirm_admission_external_identity(
    *,
    external_identity: str | None = None,
    contact: str | None = None,
    guardian: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    match_status: str | None = "Confirmed",
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    identity_name = clean(external_identity)
    if not identity_name:
        frappe.throw(_("Admission External Identity is required."))

    request_id = clean(client_request_id)
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key("confirm_identity", user, identity_name, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key("confirm_identity", user, identity_name), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        identity_doc = _require_doc_read(user, "Admission External Identity", identity_name)
        if not frappe.has_permission("Admission External Identity", ptype="write", doc=identity_doc, user=user):
            frappe.throw(_("You do not have permission to update this external identity."), frappe.PermissionError)

        status_value = clean(match_status) or "Confirmed"
        if status_value not in {"Unmatched", "Suggested", "Confirmed", "Rejected"}:
            frappe.throw(_("Invalid match status: {0}.").format(status_value))

        if clean(contact):
            _require_doc_read(user, "Contact", contact)
            identity_doc.linked_contact = clean(contact)
        if clean(guardian):
            _require_doc_read(user, "Guardian", guardian)
            identity_doc.linked_guardian = clean(guardian)
        if clean(inquiry):
            _require_doc_read(user, "Inquiry", inquiry)
            identity_doc.linked_inquiry = clean(inquiry)
        if clean(student_applicant):
            _require_doc_read(user, "Student Applicant", student_applicant)
            identity_doc.linked_student_applicant = clean(student_applicant)

        identity_doc.match_status = status_value
        identity_doc.save(ignore_permissions=True)

        response = {
            "ok": True,
            "external_identity": {
                "name": identity_doc.name,
                "match_status": identity_doc.match_status,
                "linked_contact": identity_doc.linked_contact,
                "linked_guardian": identity_doc.linked_guardian,
                "linked_inquiry": identity_doc.linked_inquiry,
                "linked_student_applicant": identity_doc.linked_student_applicant,
            },
        }
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return response
