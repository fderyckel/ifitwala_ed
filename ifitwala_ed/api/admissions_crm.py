from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import (
    assign_inquiry,
    from_inquiry_invite,
    reassign_inquiry,
)
from ifitwala_ed.admission.admissions_crm_domain import clean, get_channel_account_context
from ifitwala_ed.admission.admissions_crm_permissions import (
    doc_is_in_admissions_crm_scope,
    ensure_admissions_crm_permission,
    is_admissions_crm_user,
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


def _run_idempotent(*, user: str, action: str, target: str, client_request_id: str | None, fn):
    request_id = clean(client_request_id)
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key(action, user, target, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key(action, user, target), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        response = fn()
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return response


def _require_doc_read(user: str, doctype: str, name: str | None):
    docname = clean(name)
    if not docname:
        return None
    doc = frappe.get_doc(doctype, docname)
    if not frappe.has_permission(doctype, ptype="read", doc=doc, user=user):
        frappe.throw(
            _("You do not have permission to use {doctype} {docname}.").format(
                doctype=doctype,
                docname=docname,
            ),
            frappe.PermissionError,
        )
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
            "activity_channel",
            "outcome",
            "next_action_on",
            "staff_user",
            "activity_at",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _inquiry_summary(inquiry_name: str) -> dict:
    row = frappe.db.get_value(
        "Inquiry",
        inquiry_name,
        [
            "name",
            "workflow_state",
            "assigned_to",
            "assignment_lane",
            "archive_reason",
            "organization",
            "school",
            "student_applicant",
            "first_contacted_at",
            "followup_due_on",
            "sla_status",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _applicant_summary(applicant_name: str) -> dict:
    row = frappe.db.get_value(
        "Student Applicant",
        applicant_name,
        ["name", "application_status", "organization", "school", "inquiry"],
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


def _require_inquiry_write(user: str, inquiry: str):
    inquiry_name = clean(inquiry)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))
    doc = frappe.get_doc("Inquiry", inquiry_name)
    if not frappe.has_permission("Inquiry", ptype="write", doc=doc, user=user):
        frappe.throw(_("You do not have permission to update this Inquiry."), frappe.PermissionError)
    return doc


def _validate_crm_assignee(*, user: str, assigned_to: str, organization: str | None, school: str | None) -> None:
    assignee = clean(assigned_to)
    if not assignee:
        frappe.throw(_("Assigned To is required."))
    enabled = frappe.db.get_value("User", assignee, "enabled")
    if not enabled:
        frappe.throw(_("Assigned To must be an enabled admissions CRM user."))
    if not is_admissions_crm_user(assignee):
        frappe.throw(_("Assigned To must have an admissions CRM role."))
    if not doc_is_in_admissions_crm_scope(user=assignee, organization=organization, school=school):
        frappe.throw(_("Assigned To is outside this admissions CRM scope."))
    _assert_scope_allowed(user, organization=organization, school=school)


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
        frappe.throw(_("Admission External Identity not found: {identity}").format(identity=identity_name))

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


def _valid_inquiry_option(fieldname: str, value: str | None) -> str | None:
    text = clean(value)
    if not text:
        return None
    field = frappe.get_meta("Inquiry").get_field(fieldname)
    options = {clean(option) for option in (field.options or "").splitlines() if clean(option)}
    if text not in options:
        frappe.throw(_("Invalid Inquiry {field}: {value}.").format(field=field.label or fieldname, value=text))
    return text


def _valid_activity_option(fieldname: str, value: str | None) -> str | None:
    text = clean(value)
    if not text:
        return None
    field = frappe.get_meta("Admission CRM Activity").get_field(fieldname)
    options = {clean(option) for option in (field.options or "").splitlines() if clean(option)}
    if text not in options:
        frappe.throw(
            _("Invalid Admission CRM Activity {field}: {value}.").format(
                field=field.label or fieldname,
                value=text,
            )
        )
    return text


def _source_from_channel(channel_type: str | None) -> str:
    channel = clean(channel_type)
    if channel == "WhatsApp":
        return "WhatsApp"
    if channel == "Line":
        return "Line"
    if channel in {"Facebook Messenger", "Instagram DM"}:
        return "Facebook"
    return "Other"


def _name_parts(display_name: str | None, fallback: str | None) -> tuple[str | None, str | None]:
    text = clean(display_name) or clean(fallback)
    if not text:
        return None, None
    parts = text.split()
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _append_if_clean(payload: dict, fieldname: str, value: str | None) -> None:
    text = clean(value)
    if text:
        payload[fieldname] = text


def _inquiry_payload_for_intake(
    *,
    organization: str,
    school: str | None,
    type_of_inquiry: str,
    source: str,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    phone_number: str | None,
    student_first_name: str | None,
    student_last_name: str | None,
    intended_academic_year: str | None,
    grade_level_interest: str | None,
    program_interest: str | None,
    student_name_or_id: str | None,
    relationship_to_student: str | None,
    organization_name: str | None,
    partnership_context: str | None,
    message: str | None,
) -> dict:
    payload = {
        "doctype": "Inquiry",
        "type_of_inquiry": type_of_inquiry,
        "source": source,
        "organization": organization,
    }
    _append_if_clean(payload, "school", school)
    _append_if_clean(payload, "first_name", first_name)
    _append_if_clean(payload, "last_name", last_name)
    _append_if_clean(payload, "email", email)
    _append_if_clean(payload, "phone_number", phone_number)
    _append_if_clean(payload, "message", message)

    if type_of_inquiry == "Admission":
        _append_if_clean(payload, "student_first_name", student_first_name)
        _append_if_clean(payload, "student_last_name", student_last_name)
        _append_if_clean(payload, "intended_academic_year", intended_academic_year)
        _append_if_clean(payload, "grade_level_interest", grade_level_interest)
        _append_if_clean(payload, "program_interest", program_interest)
    elif type_of_inquiry == "Current Family":
        _append_if_clean(payload, "student_name_or_id", student_name_or_id)
        _append_if_clean(payload, "relationship_to_student", relationship_to_student)
    elif type_of_inquiry == "Partnership / Agent":
        _append_if_clean(payload, "organization_name", organization_name)
        _append_if_clean(payload, "partnership_context", partnership_context)

    return payload


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
            frappe.throw(_("Invalid match status: {status}.").format(status=status_value))

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


@frappe.whitelist()
def create_admissions_intake(
    *,
    organization: str | None = None,
    school: str | None = None,
    type_of_inquiry: str | None = None,
    source: str | None = None,
    activity_channel: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
    student_first_name: str | None = None,
    student_last_name: str | None = None,
    intended_academic_year: str | None = None,
    grade_level_interest: str | None = None,
    program_interest: str | None = None,
    student_name_or_id: str | None = None,
    relationship_to_student: str | None = None,
    organization_name: str | None = None,
    partnership_context: str | None = None,
    message: str | None = None,
    activity_type: str | None = None,
    outcome: str | None = None,
    note: str | None = None,
    next_action_on: str | None = None,
    assigned_to: str | None = None,
    assignment_lane: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    scope_organization = clean(organization)
    school_name = clean(school)
    if not scope_organization:
        frappe.throw(_("Organization is required."))

    type_value = _valid_inquiry_option("type_of_inquiry", type_of_inquiry)
    source_value = _valid_inquiry_option("source", source)
    activity_type_value = _valid_activity_option("activity_type", activity_type)
    activity_channel_value = _valid_activity_option("activity_channel", activity_channel)
    if not type_value:
        frappe.throw(_("Type of Inquiry is required."))
    if not source_value:
        frappe.throw(_("Source is required."))
    if not activity_type_value:
        frappe.throw(_("Activity Type is required."))
    if not activity_channel_value:
        frappe.throw(_("Activity Channel is required."))

    if not any(
        clean(value)
        for value in (
            first_name,
            last_name,
            email,
            phone_number,
            organization_name,
            message,
            note,
        )
    ):
        frappe.throw(_("At least one contact detail, organization name, message, or intake note is required."))

    _assert_scope_allowed(user, organization=scope_organization, school=school_name)
    assignee = clean(assigned_to)
    if assignee:
        _validate_crm_assignee(user=user, assigned_to=assignee, organization=scope_organization, school=school_name)

    def action():
        inquiry_doc = frappe.get_doc(
            _inquiry_payload_for_intake(
                organization=scope_organization,
                school=school_name,
                type_of_inquiry=type_value,
                source=source_value,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                student_first_name=student_first_name,
                student_last_name=student_last_name,
                intended_academic_year=intended_academic_year,
                grade_level_interest=grade_level_interest,
                program_interest=program_interest,
                student_name_or_id=student_name_or_id,
                relationship_to_student=relationship_to_student,
                organization_name=organization_name,
                partnership_context=partnership_context,
                message=message,
            )
        )
        inquiry_doc.insert(ignore_permissions=True)

        conversation_doc = frappe.get_doc(
            {
                "doctype": "Admission Conversation",
                "inquiry": inquiry_doc.name,
            }
        )
        conversation_doc.insert(ignore_permissions=True)

        activity_doc = frappe.get_doc(
            {
                "doctype": "Admission CRM Activity",
                "conversation": conversation_doc.name,
                "activity_type": activity_type_value,
                "activity_channel": activity_channel_value,
                "outcome": clean(outcome),
                "note": clean(note),
                "next_action_on": clean(next_action_on),
            }
        )
        activity_doc.insert(ignore_permissions=True)

        assignment_result = None
        if assignee:
            conversation_doc.reload()
            conversation_doc.assigned_to = assignee
            conversation_doc.save(ignore_permissions=True)
            assignment_result = assign_inquiry(
                "Inquiry",
                inquiry_doc.name,
                assignee,
                assignment_lane=assignment_lane,
            )

        return {
            "ok": True,
            "inquiry": _inquiry_summary(inquiry_doc.name),
            "conversation": _conversation_summary(conversation_doc.name),
            "activity": _activity_summary(activity_doc.name),
            "assignment": assignment_result,
        }

    return _run_idempotent(
        user=user,
        action="create_admissions_intake",
        target=scope_organization,
        client_request_id=client_request_id,
        fn=action,
    )


@frappe.whitelist()
def assign_admission_conversation(
    *,
    conversation: str | None = None,
    assigned_to: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    conversation_name = clean(conversation)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))

    def action():
        doc = _require_conversation_write(user, conversation_name)
        assignee = clean(assigned_to)
        _validate_crm_assignee(
            user=user,
            assigned_to=assignee,
            organization=doc.organization,
            school=doc.school,
        )
        if clean(doc.assigned_to) == assignee:
            return {"ok": True, "changed": False, "conversation": _conversation_summary(doc.name)}

        doc.assigned_to = assignee
        doc.save(ignore_permissions=True)
        doc.add_comment(
            "Comment",
            text=_("Admissions conversation assigned to {user}.").format(user=frappe.bold(assignee)),
        )
        return {"ok": True, "changed": True, "conversation": _conversation_summary(doc.name)}

    return _run_idempotent(
        user=user,
        action="assign_conversation",
        target=conversation_name,
        client_request_id=client_request_id,
        fn=action,
    )


@frappe.whitelist()
def update_admission_conversation_status(
    *,
    conversation: str | None = None,
    status: str | None = None,
    note: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    conversation_name = clean(conversation)
    status_value = clean(status)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))
    if status_value not in {"Open", "Closed", "Archived", "Spam"}:
        frappe.throw(_("Invalid Admission Conversation status: {status}.").format(status=status_value))

    def action():
        doc = _require_conversation_write(user, conversation_name)
        changed = clean(doc.status) != status_value
        doc.status = status_value
        if status_value != "Open":
            doc.needs_reply = 0
        doc.save(ignore_permissions=True)

        activity_name = None
        note_text = clean(note)
        if status_value != "Open" or note_text:
            activity_doc = frappe.get_doc(
                {
                    "doctype": "Admission CRM Activity",
                    "conversation": doc.name,
                    "activity_type": "Archived" if status_value in {"Closed", "Archived", "Spam"} else "Note",
                    "outcome": status_value,
                    "note": note_text,
                }
            )
            activity_doc.insert(ignore_permissions=True)
            activity_name = activity_doc.name

        doc.add_comment(
            "Comment",
            text=_("Admissions conversation status set to {status}.").format(status=frappe.bold(status_value)),
        )
        response = {"ok": True, "changed": changed, "conversation": _conversation_summary(doc.name)}
        if activity_name:
            response["activity"] = _activity_summary(activity_name)
        return response

    return _run_idempotent(
        user=user,
        action="conversation_status",
        target=conversation_name,
        client_request_id=client_request_id,
        fn=action,
    )


@frappe.whitelist()
def create_inquiry_from_admission_conversation(
    *,
    conversation: str | None = None,
    type_of_inquiry: str | None = None,
    source: str | None = None,
    message: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    conversation_name = clean(conversation)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))

    def action():
        conversation_doc = _require_conversation_write(user, conversation_name)
        existing_inquiry = clean(conversation_doc.inquiry)
        if existing_inquiry:
            return {
                "ok": True,
                "changed": False,
                "conversation": _conversation_summary(conversation_doc.name),
                "inquiry": _inquiry_summary(existing_inquiry),
            }

        _assert_scope_allowed(user, organization=conversation_doc.organization, school=conversation_doc.school)
        identity = {}
        if clean(conversation_doc.external_identity):
            identity = (
                frappe.db.get_value(
                    "Admission External Identity",
                    conversation_doc.external_identity,
                    ["display_name", "email", "phone_number", "channel_type"],
                    as_dict=True,
                )
                or {}
            )

        first_name, last_name = _name_parts(identity.get("display_name"), conversation_doc.title)
        source_value = _valid_inquiry_option("source", source) or _source_from_channel(identity.get("channel_type"))
        type_value = _valid_inquiry_option("type_of_inquiry", type_of_inquiry) or "Admission"

        inquiry_doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": first_name,
                "last_name": last_name,
                "email": clean(identity.get("email")),
                "phone_number": clean(identity.get("phone_number")),
                "type_of_inquiry": type_value,
                "source": source_value,
                "organization": conversation_doc.organization,
                "school": conversation_doc.school,
                "message": clean(message) or clean(conversation_doc.last_message_preview),
            }
        )
        inquiry_doc.insert(ignore_permissions=True)

        conversation_doc.inquiry = inquiry_doc.name
        conversation_doc.save(ignore_permissions=True)
        conversation_doc.add_comment(
            "Comment",
            text=_("Inquiry {inquiry} created from this admissions conversation.").format(
                inquiry=frappe.bold(inquiry_doc.name)
            ),
        )
        return {
            "ok": True,
            "changed": True,
            "conversation": _conversation_summary(conversation_doc.name),
            "inquiry": _inquiry_summary(inquiry_doc.name),
        }

    return _run_idempotent(
        user=user,
        action="create_inquiry_from_conversation",
        target=conversation_name,
        client_request_id=client_request_id,
        fn=action,
    )


@frappe.whitelist()
def assign_inquiry_from_inbox(
    *,
    inquiry: str | None = None,
    assigned_to: str | None = None,
    assignment_lane: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    assignee = clean(assigned_to)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))
    if not assignee:
        frappe.throw(_("Assigned To is required."))

    def action():
        doc = _require_inquiry_write(user, inquiry_name)
        if clean(doc.assigned_to) == assignee:
            return {"ok": True, "changed": False, "inquiry": _inquiry_summary(doc.name)}

        if clean(doc.assigned_to):
            result = reassign_inquiry("Inquiry", doc.name, assignee, assignment_lane=assignment_lane)
        else:
            result = assign_inquiry("Inquiry", doc.name, assignee, assignment_lane=assignment_lane)

        return {"ok": True, "changed": True, "result": result, "inquiry": _inquiry_summary(doc.name)}

    return _run_idempotent(
        user=user,
        action="assign_inquiry",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )


@frappe.whitelist()
def archive_inquiry_from_inbox(
    *,
    inquiry: str | None = None,
    reason: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    archive_reason = clean(reason)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))
    if not archive_reason:
        frappe.throw(_("Archive reason is required."))

    def action():
        doc = _require_inquiry_write(user, inquiry_name)
        if clean(doc.workflow_state) == "Archived" and clean(doc.archive_reason):
            return {"ok": True, "changed": False, "inquiry": _inquiry_summary(doc.name)}
        result = doc.archive(reason=archive_reason)
        return {
            "ok": True,
            "changed": bool(result.get("changed")),
            "result": result,
            "inquiry": _inquiry_summary(doc.name),
        }

    return _run_idempotent(
        user=user,
        action="archive_inquiry",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )


@frappe.whitelist()
def mark_inquiry_contacted_from_inbox(
    *,
    inquiry: str | None = None,
    complete_todo: int | str | None = 0,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))

    def action():
        doc = _require_inquiry_write(user, inquiry_name)
        if clean(doc.workflow_state) in {"Contacted", "Qualified"}:
            return {"ok": True, "changed": False, "inquiry": _inquiry_summary(doc.name)}
        result = doc.mark_contacted(complete_todo=frappe.utils.cint(complete_todo))
        return {"ok": True, "changed": True, "result": result, "inquiry": _inquiry_summary(doc.name)}

    return _run_idempotent(
        user=user,
        action="mark_inquiry_contacted",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )


@frappe.whitelist()
def qualify_inquiry_from_inbox(
    *,
    inquiry: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))

    def action():
        doc = _require_inquiry_write(user, inquiry_name)
        if clean(doc.workflow_state) == "Qualified":
            return {"ok": True, "changed": False, "inquiry": _inquiry_summary(doc.name)}
        result = doc.mark_qualified()
        return {
            "ok": True,
            "changed": bool(result.get("changed")),
            "result": result,
            "inquiry": _inquiry_summary(doc.name),
        }

    return _run_idempotent(
        user=user,
        action="qualify_inquiry",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )


@frappe.whitelist()
def invite_inquiry_to_apply_from_inbox(
    *,
    inquiry: str | None = None,
    school: str | None = None,
    organization: str | None = None,
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    inquiry_name = clean(inquiry)
    school_name = clean(school)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))
    if not school_name:
        frappe.throw(_("School is required to invite an applicant."))

    def action():
        _require_inquiry_write(user, inquiry_name)
        applicant_name = from_inquiry_invite(
            inquiry_name=inquiry_name,
            school=school_name,
            organization=clean(organization) or None,
        )
        return {
            "ok": True,
            "student_applicant": _applicant_summary(applicant_name),
            "inquiry": _inquiry_summary(inquiry_name),
        }

    return _run_idempotent(
        user=user,
        action="invite_inquiry",
        target=inquiry_name,
        client_request_id=client_request_id,
        fn=action,
    )
