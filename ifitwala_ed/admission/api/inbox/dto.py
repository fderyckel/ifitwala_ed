from __future__ import annotations

from datetime import date, datetime
from typing import Any
from urllib.parse import quote

from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.admissions_crm_domain import clean


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _as_bool(value: Any) -> bool:
    return bool(cint(value))


def _name_from_parts(*parts: str | None, fallback: str) -> str:
    text = " ".join(clean(part) for part in parts if clean(part)).strip()
    return text or fallback


def _subtitle(parts: list[str | None]) -> str | None:
    cleaned = [clean(part) for part in parts if clean(part)]
    return " • ".join(cleaned) if cleaned else None


def _base_row() -> dict:
    return {
        "unread_count": 0,
        "permissions": {"can_open": True},
        "actions": [],
    }


def _desk_url(doctype: str, name: str | None) -> str | None:
    docname = clean(name)
    if not docname:
        return None
    doctype_slug = doctype.strip().lower().replace(" ", "-")
    return f"/desk/{doctype_slug}/{quote(docname, safe='')}"


def _conversation_actions(row: dict) -> list[dict]:
    actions = [
        {"id": "log_reply", "enabled": True},
        {"id": "record_activity", "enabled": True},
        {"id": "assign_owner" if not clean(row.get("assigned_to")) else "reassign_owner", "enabled": True},
    ]
    if clean(row.get("status")) == "Open" and not clean(row.get("inquiry")):
        actions.append({"id": "create_inquiry", "enabled": True})
        actions.append({"id": "link_inquiry", "enabled": True})
    if not clean(row.get("student_applicant")):
        actions.append({"id": "link_applicant", "enabled": True})
    if clean(row.get("external_identity")):
        actions.append({"id": "resolve_identity_match", "enabled": True})
    if clean(row.get("status")) == "Open":
        actions.append({"id": "archive_conversation", "enabled": True})
        actions.append({"id": "mark_spam", "enabled": True})
    return actions


def _inquiry_actions(row: dict) -> list[dict]:
    state = clean(row.get("workflow_state"))
    actions = [{"id": "log_message", "enabled": True}]
    actions.append({"id": "assign_owner" if not clean(row.get("assigned_to")) else "reassign_owner", "enabled": True})
    if state in {"New", "Assigned"}:
        actions.append({"id": "mark_contacted", "enabled": True})
    if state == "Contacted":
        actions.append({"id": "qualify", "enabled": True})
    if state == "Qualified" and not clean(row.get("student_applicant")):
        actions.append({"id": "invite_to_apply", "enabled": True})
    if state != "Archived":
        actions.append({"id": "archive_inquiry", "enabled": True})
    return actions


def _applicant_actions(*, has_conversation: bool) -> list[dict]:
    return [
        {"id": "open_applicant", "enabled": True},
        {
            "id": "record_activity",
            "enabled": has_conversation,
            "disabled_reason": None if has_conversation else _("Link or create an admissions CRM conversation first."),
        },
    ]


def _applicant_case_actions() -> list[dict]:
    return [
        {"id": "reply_applicant_case", "enabled": True},
        {"id": "open_applicant", "enabled": True},
    ]


def _conversation_dto(row: dict) -> dict:
    stage = "applicant" if clean(row.get("student_applicant")) else "pre_applicant"
    channel_label = clean(row.get("channel_account_label")) or clean(row.get("channel_type"))
    identity_label = clean(row.get("external_identity_label")) or clean(row.get("external_identity"))
    dto = {
        **_base_row(),
        "id": f"conversation:{row.get('name')}",
        "kind": "conversation",
        "stage": stage,
        "title": clean(row.get("title")) or clean(row.get("name")),
        "subtitle": _subtitle([channel_label, identity_label, clean(row.get("status"))]),
        "organization": clean(row.get("organization")),
        "school": clean(row.get("school")),
        "inquiry": clean(row.get("inquiry")),
        "student_applicant": clean(row.get("student_applicant")),
        "conversation": clean(row.get("name")),
        "open_url": _desk_url("Admission Conversation", row.get("name")),
        "external_identity": clean(row.get("external_identity")),
        "channel_type": clean(row.get("channel_type")),
        "channel_account": clean(row.get("channel_account")),
        "owner": clean(row.get("assigned_to")),
        "sla_state": None,
        "last_activity_at": _as_text(
            row.get("latest_message_at") or row.get("last_activity_at") or row.get("modified")
        ),
        "last_message_preview": clean(row.get("last_message_preview")),
        "needs_reply": _as_bool(row.get("needs_reply")),
        "next_action_on": _as_text(row.get("next_action_on")),
    }
    dto["permissions"].update(
        {
            "can_reply": True,
            "can_record_activity": True,
            "can_link": True,
        }
    )
    dto["actions"] = _conversation_actions(row)
    return dto


def _inquiry_dto(row: dict, conversation: dict | None = None) -> dict:
    title = _name_from_parts(row.get("first_name"), row.get("last_name"), fallback=clean(row.get("name")) or "Inquiry")
    preview = clean(row.get("next_action_note")) or clean(row.get("message"))
    conversation_next_action = conversation.get("next_action_on") if conversation else None
    conversation_activity = conversation.get("last_activity_at") if conversation else None
    dto = {
        **_base_row(),
        "id": f"inquiry:{row.get('name')}",
        "kind": "inquiry",
        "stage": "inquiry",
        "title": title,
        "subtitle": _subtitle([clean(row.get("type_of_inquiry")), clean(row.get("source")), clean(row.get("email"))]),
        "organization": clean(row.get("organization")),
        "school": clean(row.get("school")),
        "inquiry": clean(row.get("name")),
        "student_applicant": clean(row.get("student_applicant")),
        "conversation": clean(conversation.get("name")) if conversation else None,
        "open_url": _desk_url("Inquiry", row.get("name")),
        "external_identity": clean(conversation.get("external_identity")) if conversation else None,
        "channel_type": clean(conversation.get("channel_type")) if conversation else None,
        "channel_account": clean(conversation.get("channel_account")) if conversation else None,
        "owner": clean(row.get("assigned_to")),
        "sla_state": clean(row.get("sla_status")),
        "last_activity_at": _as_text(conversation_activity or row.get("modified") or row.get("submitted_at")),
        "last_message_preview": preview,
        "needs_reply": False,
        "next_action_on": _as_text(
            conversation_next_action or row.get("followup_due_on") or row.get("first_contact_due_on")
        ),
    }
    dto["permissions"].update(
        {
            "can_log_message": True,
            "can_mark_contacted": clean(row.get("workflow_state")) in {"New", "Assigned"},
            "can_invite": clean(row.get("workflow_state")) == "Qualified" and not clean(row.get("student_applicant")),
        }
    )
    dto["actions"] = _inquiry_actions(row)
    return dto


def _applicant_dto(row: dict, conversation: dict | None = None, case_summary: dict | None = None) -> dict:
    title = clean(row.get("title")) or _name_from_parts(
        row.get("first_name"),
        row.get("last_name"),
        fallback=clean(row.get("name")) or "Student Applicant",
    )
    summary = case_summary or {}
    dto = {
        **_base_row(),
        "id": f"student_applicant:{row.get('name')}",
        "kind": "student_applicant",
        "stage": "applicant",
        "title": title,
        "subtitle": _subtitle(
            [clean(row.get("application_status")), clean(row.get("program")), clean(row.get("applicant_email"))]
        ),
        "organization": clean(row.get("organization")),
        "school": clean(row.get("school")),
        "inquiry": clean(row.get("inquiry")),
        "student_applicant": clean(row.get("name")),
        "conversation": clean(conversation.get("name")) if conversation else None,
        "open_url": _desk_url("Student Applicant", row.get("name")),
        "external_identity": clean(conversation.get("external_identity")) if conversation else None,
        "channel_type": clean(conversation.get("channel_type")) if conversation else None,
        "channel_account": clean(conversation.get("channel_account")) if conversation else None,
        "owner": clean(conversation.get("assigned_to")) if conversation else None,
        "sla_state": clean(row.get("application_status")),
        "last_activity_at": _as_text(summary.get("last_message_at") or row.get("modified") or row.get("submitted_at")),
        "last_message_preview": clean(summary.get("last_message_preview")),
        "needs_reply": _as_bool(summary.get("needs_reply")),
        "unread_count": cint(summary.get("unread_count") or 0),
        "next_action_on": None,
        "org_communication": clean(summary.get("thread_name")),
    }
    dto["permissions"].update(
        {
            "can_open_applicant": True,
            "can_record_activity": bool(conversation),
            "can_reply_applicant_case": bool(clean(summary.get("thread_name"))),
        }
    )
    dto["actions"] = _applicant_actions(has_conversation=bool(conversation))
    return dto


def _applicant_message_dto(row: dict, case_summary: dict, conversation: dict | None = None) -> dict:
    title = clean(row.get("title")) or _name_from_parts(
        row.get("first_name"),
        row.get("last_name"),
        fallback=clean(row.get("name")) or "Student Applicant",
    )
    dto = {
        **_base_row(),
        "id": f"applicant_message:{case_summary.get('thread_name')}:{row.get('name')}",
        "kind": "applicant_message",
        "stage": "applicant",
        "title": title,
        "subtitle": _subtitle(
            [_("Applicant Case Message"), clean(row.get("application_status")), clean(row.get("applicant_email"))]
        ),
        "organization": clean(row.get("organization")),
        "school": clean(row.get("school")),
        "inquiry": clean(row.get("inquiry")),
        "student_applicant": clean(row.get("name")),
        "conversation": clean(conversation.get("name")) if conversation else None,
        "open_url": _desk_url("Student Applicant", row.get("name")),
        "external_identity": clean(conversation.get("external_identity")) if conversation else None,
        "channel_type": None,
        "channel_account": None,
        "owner": clean(conversation.get("assigned_to")) if conversation else None,
        "sla_state": clean(row.get("application_status")),
        "last_activity_at": _as_text(case_summary.get("last_message_at") or row.get("modified")),
        "last_message_preview": clean(case_summary.get("last_message_preview")),
        "needs_reply": _as_bool(case_summary.get("needs_reply")),
        "unread_count": cint(case_summary.get("unread_count") or 0),
        "next_action_on": None,
        "org_communication": clean(case_summary.get("thread_name")),
    }
    dto["permissions"].update({"can_open_applicant": True, "can_reply_applicant_case": True})
    dto["actions"] = _applicant_case_actions()
    return dto
