# ifitwala_ed/admission/api/crm/conversations.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean, get_channel_account_context
from ifitwala_ed.admission.admissions_crm_permissions import ensure_admissions_crm_permission
from ifitwala_ed.admission.api.crm.guards import (
    _assert_scope_allowed,
    _require_conversation_write,
    _require_doc_read,
    _validate_crm_assignee,
)
from ifitwala_ed.admission.api.crm.idempotency import (
    IDEMPOTENCY_TTL_SECONDS,
    _cache,
    _idempotency_key,
    _lock_key,
    _run_idempotent,
)
from ifitwala_ed.admission.api.crm.summaries import _activity_summary, _conversation_summary


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


def link_admission_conversation_impl(
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


def assign_admission_conversation_impl(
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


def update_admission_conversation_status_impl(
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
