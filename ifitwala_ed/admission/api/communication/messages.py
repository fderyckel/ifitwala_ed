from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.api.communication.constants import MESSAGE_LIMIT
from ifitwala_ed.admission.api.communication.context import (
    _normalize_context,
    _require_actor_context,
    _to_text,
)
from ifitwala_ed.admission.api.communication.read_receipts import _count_unread_messages
from ifitwala_ed.admission.api.communication.threads import _get_or_create_thread, _get_thread_name
from ifitwala_ed.api.org_communication_interactions import (
    create_interaction_entry,
    get_latest_org_communication_entry_for_user,
)
from ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry import (
    DOCTYPE as ENTRY_DOCTYPE,
)


def _sender_direction(
    *,
    sender_user: str,
    applicant_user: str,
    visibility: str,
    portal_actor_user: str | None = None,
) -> str:
    if (applicant_user and sender_user == applicant_user) or (portal_actor_user and sender_user == portal_actor_user):
        return "ApplicantToStaff"
    if visibility == "Public to audience":
        return "StaffToApplicant"
    return "Internal"


def _truncate_preview(note: str, max_len: int = 120) -> str:
    text = " ".join((note or "").split())
    if len(text) <= max_len:
        return text
    return f"{text[:max_len].rstrip()}..."


def _fetch_latest_entry_for_sender(*, thread_name: str, sender_user: str) -> dict | None:
    return get_latest_org_communication_entry_for_user(
        org_communication=thread_name,
        user=sender_user,
    )


def _save_case_interaction(
    *,
    thread_name: str,
    actor_user: str,
    intent_type: str,
    note: str,
    visibility: str,
) -> dict:
    saved_row = create_interaction_entry(
        org_communication=thread_name,
        user=actor_user,
        intent_type=intent_type,
        note=note,
        visibility=visibility,
        surface="Other",
    )

    return {
        "name": _to_text(saved_row.get("name")),
        "user": _to_text(saved_row.get("user")),
        "note": _to_text(saved_row.get("note")),
        "visibility": _to_text(saved_row.get("visibility")),
        "creation": saved_row.get("creation"),
        "modified": saved_row.get("modified"),
    }


def _serialize_message_row(*, row: dict, applicant_user: str, portal_actor_user: str | None = None) -> dict:
    sender_user = _to_text(row.get("user"))
    visibility = _to_text(row.get("visibility"))
    note = _to_text(row.get("note"))
    direction = _sender_direction(
        sender_user=sender_user,
        applicant_user=applicant_user,
        visibility=visibility,
        portal_actor_user=_to_text(portal_actor_user),
    )
    full_name = _to_text(row.get("full_name")) or _to_text(
        frappe.db.get_value("User", sender_user, "full_name") if sender_user else None
    )
    full_name = full_name or sender_user
    return {
        "name": _to_text(row.get("name")),
        "user": sender_user,
        "full_name": full_name,
        "body": note,
        "direction": direction,
        "visibility": visibility,
        "applicant_visible": bool(
            visibility == "Public to audience"
            or (applicant_user and sender_user == applicant_user)
            or (_to_text(portal_actor_user) and sender_user == _to_text(portal_actor_user))
        ),
        "created_at": row.get("creation"),
        "modified_at": row.get("modified"),
    }


def send_admissions_case_message_impl(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    body: str | None = None,
    applicant_visible: int | None = 1,
    client_request_id: str | None = None,
):
    context_doctype, context_name = _normalize_context(context_doctype, context_name)
    actor_ctx = _require_actor_context(context_doctype=context_doctype, context_name=context_name)

    note = _to_text(body)
    if not note:
        frappe.throw(_("Message body is required."))
    if len(note) > MESSAGE_LIMIT:
        frappe.throw(
            _("Message body cannot exceed {character_limit} characters.").format(character_limit=MESSAGE_LIMIT)
        )

    is_applicant = actor_ctx.get("actor") == "applicant"
    visible_to_applicant = True if is_applicant else bool(cint(applicant_visible))

    intent_type = "Question" if is_applicant else ("Other" if visible_to_applicant else "Concern")
    visibility = (
        "Private to school" if is_applicant else ("Public to audience" if visible_to_applicant else "Private to school")
    )

    thread_name = _get_or_create_thread(
        context_doctype=context_doctype,
        context_name=context_name,
        context_row=actor_ctx.get("context") or {},
    )

    user = _to_text(actor_ctx.get("user"))
    request_id = _to_text(client_request_id)
    cache_key = None
    if request_id:
        cache_key = f"admissions:message:{user}:{thread_name}:{request_id}"
        cached = frappe.cache().get_value(cache_key)
        if cached:
            parsed = frappe.parse_json(cached)
            if isinstance(parsed, dict):
                return parsed

    saved_row = _save_case_interaction(
        thread_name=thread_name,
        actor_user=user,
        intent_type=intent_type,
        note=note,
        visibility=visibility,
    )
    latest = _fetch_latest_entry_for_sender(thread_name=thread_name, sender_user=user) or saved_row

    response = {
        "thread_name": thread_name,
        "message": _serialize_message_row(
            row=latest,
            applicant_user=_to_text(actor_ctx.get("applicant_user")),
            portal_actor_user=_to_text(actor_ctx.get("portal_actor_user")),
        ),
    }

    if cache_key:
        frappe.cache().set_value(cache_key, frappe.as_json(response), expires_in_sec=600)

    return response


def get_admissions_case_thread_impl(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    limit_start: int | None = 0,
    limit: int | None = 60,
):
    context_doctype, context_name = _normalize_context(context_doctype, context_name)
    actor_ctx = _require_actor_context(context_doctype=context_doctype, context_name=context_name)

    thread_name = _get_thread_name(context_doctype, context_name)
    if not thread_name:
        return {"thread_name": None, "messages": [], "unread_count": 0}

    start = max(0, cint(limit_start or 0))
    page_length = cint(limit or 60)
    page_length = 200 if page_length > 200 else page_length
    page_length = 1 if page_length < 1 else page_length

    actor_kind = _to_text(actor_ctx.get("actor"))
    actor_user = _to_text(actor_ctx.get("user"))
    applicant_user = _to_text(actor_ctx.get("applicant_user"))
    portal_actor_user = _to_text(actor_ctx.get("portal_actor_user"))

    conditions = [
        "i.org_communication = %(thread_name)s",
        "COALESCE(TRIM(i.note), '') != ''",
        "i.visibility != 'Hidden'",
    ]
    values = {
        "thread_name": thread_name,
        "actor_user": actor_user,
        "start": start,
        "page_length": page_length,
    }
    if actor_kind == "applicant":
        conditions.append("(i.visibility = 'Public to audience' OR i.user = %(actor_user)s)")

    where_clause = " AND ".join(conditions)
    rows = frappe.db.sql(
        f"""
        SELECT
            i.name,
            i.user,
            i.note,
            i.visibility,
            i.creation,
            i.modified,
            u.full_name
        FROM `tab{ENTRY_DOCTYPE}` i
        LEFT JOIN `tabUser` u
          ON u.name = i.user
        WHERE {where_clause}
        ORDER BY i.creation ASC
        LIMIT %(start)s, %(page_length)s
        """,
        values,
        as_dict=True,
    )

    messages = [
        _serialize_message_row(
            row=row,
            applicant_user=applicant_user,
            portal_actor_user=portal_actor_user,
        )
        for row in (rows or [])
    ]

    unread_count = _count_unread_messages(
        thread_name=thread_name,
        applicant_user=applicant_user,
        actor_user=actor_user,
        actor_kind=actor_kind,
    )

    return {
        "thread_name": thread_name,
        "messages": messages,
        "unread_count": unread_count,
    }
