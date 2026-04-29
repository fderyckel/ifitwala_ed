from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime, nowdate

from ifitwala_ed.admission.admission_utils import get_admissions_file_staff_scope
from ifitwala_ed.admission.admissions_crm_domain import clean, get_school_organization
from ifitwala_ed.admission.admissions_crm_permissions import (
    doc_is_in_admissions_crm_scope,
    ensure_admissions_crm_permission,
)
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_descendants_including_self,
    get_school_descendants_including_self,
)

DEFAULT_LIMIT = 40
MAX_LIMIT = 100
STALE_LEAD_DAYS = 14


QUEUE_IDS = (
    "needs_reply",
    "unassigned",
    "overdue_first_contact",
    "due_today",
    "qualified_not_invited",
    "invited_not_started",
    "missing_documents",
    "stale_leads",
    "unmatched_messages",
)


def _bounded_limit(value: int | str | None) -> int:
    limit = cint(value) or DEFAULT_LIMIT
    return min(max(limit, 1), MAX_LIMIT)


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _as_bool(value: Any) -> bool:
    return bool(cint(value))


def _scope_values(values) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = clean(value)
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return cleaned


def _descendant_organizations(organization: str | None) -> list[str]:
    organization_name = clean(organization)
    if not organization_name:
        return []
    return _scope_values(get_organization_descendants_including_self(organization_name))


def _descendant_schools(school: str | None) -> list[str]:
    school_name = clean(school)
    if not school_name:
        return []
    return _scope_values(get_school_descendants_including_self(school_name))


def _resolve_scope(user: str, *, organization: str | None = None, school: str | None = None) -> dict:
    organization_name = clean(organization)
    school_name = clean(school)

    if school_name and not organization_name:
        organization_name = get_school_organization(school_name)
    if school_name and organization_name:
        school_org = get_school_organization(school_name)
        if school_org and school_org != organization_name:
            if school_org not in _descendant_organizations(organization_name):
                frappe.throw(_("Selected School does not belong to the selected Organization."))

    if organization_name or school_name:
        if not doc_is_in_admissions_crm_scope(user=user, organization=organization_name, school=school_name):
            frappe.throw(_("You do not have permission for this admissions inbox scope."), frappe.PermissionError)

    staff_scope = get_admissions_file_staff_scope(user)
    if not staff_scope.get("allowed"):
        frappe.throw(_("You do not have permission to access Admissions Inbox."), frappe.PermissionError)

    return {
        "bypass": bool(staff_scope.get("bypass")),
        "organization": organization_name,
        "school": school_name,
        "org_scope": _scope_values(staff_scope.get("org_scope") or []),
        "school_scope": _scope_values(staff_scope.get("school_scope") or []),
        "filter_orgs": _descendant_organizations(organization_name) if organization_name else [],
        "filter_schools": _descendant_schools(school_name) if school_name else [],
    }


def _add_in_tuple_condition(
    conditions: list[str], params: dict, *, alias: str, field: str, key: str, values: list[str]
):
    cleaned = _scope_values(values)
    if not cleaned:
        conditions.append("1=0")
        return
    conditions.append(f"{alias}.{field} IN %({key})s")
    params[key] = tuple(cleaned)


def _apply_scope_conditions(conditions: list[str], params: dict, *, alias: str, scope: dict) -> None:
    if scope.get("filter_orgs"):
        _add_in_tuple_condition(
            conditions,
            params,
            alias=alias,
            field="organization",
            key=f"{alias}_filter_orgs",
            values=scope["filter_orgs"],
        )
    if scope.get("filter_schools"):
        _add_in_tuple_condition(
            conditions,
            params,
            alias=alias,
            field="school",
            key=f"{alias}_filter_schools",
            values=scope["filter_schools"],
        )
    if scope.get("filter_orgs") or scope.get("filter_schools"):
        return

    if scope.get("bypass"):
        return

    org_scope = _scope_values(scope.get("org_scope") or [])
    school_scope = _scope_values(scope.get("school_scope") or [])

    if org_scope:
        _add_in_tuple_condition(
            conditions,
            params,
            alias=alias,
            field="organization",
            key=f"{alias}_user_org_scope",
            values=org_scope,
        )
    if school_scope:
        conditions.append(f"(IFNULL({alias}.school, '') = '' OR {alias}.school IN %({alias}_user_school_scope)s)")
        params[f"{alias}_user_school_scope"] = tuple(school_scope)
    if not org_scope and not school_scope:
        conditions.append("1=0")


def _where_clause(conditions: list[str]) -> str:
    if not conditions:
        return ""
    return " WHERE " + " AND ".join(f"({condition})" for condition in conditions)


def _fetch_conversation_rows(*, scope: dict, limit: int) -> list[dict]:
    conditions = ["c.status != 'Spam'"]
    params = {"limit": limit * 4}
    _apply_scope_conditions(conditions, params, alias="c", scope=scope)

    return frappe.db.sql(
        f"""
        SELECT
            c.name,
            c.title,
            c.organization,
            c.school,
            c.assigned_to,
            c.status,
            c.inquiry,
            c.student_applicant,
            c.external_identity,
            c.channel_account,
            c.latest_message_at,
            c.latest_inbound_message_at,
            c.latest_outbound_message_at,
            c.needs_reply,
            c.last_message_preview,
            c.next_action_on,
            c.last_activity_at,
            c.modified,
            ca.channel_type,
            ca.display_name AS channel_account_label,
            ei.display_name AS external_identity_label,
            ei.match_status AS identity_match_status
        FROM `tabAdmission Conversation` c
        LEFT JOIN `tabAdmission Channel Account` ca
          ON ca.name = c.channel_account
        LEFT JOIN `tabAdmission External Identity` ei
          ON ei.name = c.external_identity
        {_where_clause(conditions)}
        ORDER BY COALESCE(c.latest_message_at, c.last_activity_at, c.modified) DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _fetch_inquiry_rows(*, scope: dict, limit: int) -> list[dict]:
    conditions = ["IFNULL(i.workflow_state, '') != 'Archived'"]
    params = {"limit": limit * 4}
    _apply_scope_conditions(conditions, params, alias="i", scope=scope)

    return frappe.db.sql(
        f"""
        SELECT
            i.name,
            i.first_name,
            i.last_name,
            i.email,
            i.phone_number,
            i.type_of_inquiry,
            i.source,
            i.message,
            i.next_action_note,
            i.submitted_at,
            i.workflow_state,
            i.sla_status,
            i.assigned_to,
            i.first_contact_due_on,
            i.followup_due_on,
            i.organization,
            i.school,
            i.student_applicant,
            i.modified
        FROM `tabInquiry` i
        {_where_clause(conditions)}
        ORDER BY COALESCE(i.followup_due_on, i.first_contact_due_on, DATE(i.modified)) ASC, i.modified DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _fetch_applicant_rows(*, scope: dict, limit: int) -> list[dict]:
    conditions = ["sa.application_status IN ('Invited', 'Missing Info')"]
    params = {"limit": limit * 2}
    _apply_scope_conditions(conditions, params, alias="sa", scope=scope)

    return frappe.db.sql(
        f"""
        SELECT
            sa.name,
            sa.title,
            sa.first_name,
            sa.last_name,
            sa.applicant_email,
            sa.organization,
            sa.school,
            sa.program,
            sa.academic_year,
            sa.application_status,
            sa.submitted_at,
            sa.inquiry,
            sa.modified
        FROM `tabStudent Applicant` sa
        {_where_clause(conditions)}
        ORDER BY sa.modified DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _conversation_by_inquiry(rows: list[dict]) -> dict[str, dict]:
    by_inquiry: dict[str, dict] = {}
    for row in rows:
        inquiry = clean(row.get("inquiry"))
        if inquiry and inquiry not in by_inquiry:
            by_inquiry[inquiry] = row
    return by_inquiry


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
        "last_activity_at": _as_text(row.get("modified") or row.get("submitted_at")),
        "last_message_preview": preview,
        "needs_reply": False,
        "next_action_on": _as_text(row.get("followup_due_on") or row.get("first_contact_due_on")),
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


def _applicant_dto(row: dict, conversation: dict | None = None) -> dict:
    title = clean(row.get("title")) or _name_from_parts(
        row.get("first_name"),
        row.get("last_name"),
        fallback=clean(row.get("name")) or "Student Applicant",
    )
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
        "last_activity_at": _as_text(row.get("modified") or row.get("submitted_at")),
        "last_message_preview": None,
        "needs_reply": False,
        "next_action_on": None,
    }
    dto["permissions"].update({"can_open_applicant": True, "can_record_activity": bool(conversation)})
    dto["actions"] = _applicant_actions(has_conversation=bool(conversation))
    return dto


def _queue_shell() -> OrderedDict[str, dict]:
    queues: OrderedDict[str, dict] = OrderedDict()
    for queue_id in QUEUE_IDS:
        queues[queue_id] = {
            "id": queue_id,
            "label": _queue_label(queue_id),
            "count": 0,
            "rows": [],
            "has_more": False,
        }
    return queues


def _queue_label(queue_id: str) -> str:
    if queue_id == "needs_reply":
        return _("Needs Reply")
    if queue_id == "unassigned":
        return _("Unassigned")
    if queue_id == "overdue_first_contact":
        return _("Overdue First Contact")
    if queue_id == "due_today":
        return _("Due Today")
    if queue_id == "qualified_not_invited":
        return _("Qualified Not Invited")
    if queue_id == "invited_not_started":
        return _("Invited Not Started")
    if queue_id == "missing_documents":
        return _("Missing Documents")
    if queue_id == "stale_leads":
        return _("Stale Leads")
    if queue_id == "unmatched_messages":
        return _("Unmatched Messages")
    return _("Admissions Inbox")


def _append_queue_row(queues: OrderedDict[str, dict], queue_id: str, row: dict, *, limit: int) -> None:
    queue = queues[queue_id]
    queue["count"] += 1
    if len(queue["rows"]) < limit:
        queue["rows"].append(row)
    else:
        queue["has_more"] = True


def _active_first_contact_state(row: dict) -> bool:
    return clean(row.get("workflow_state")) in {"New", "Assigned"}


def _build_queues(
    *, conversations: list[dict], inquiries: list[dict], applicants: list[dict], limit: int
) -> list[dict]:
    queues = _queue_shell()
    today = getdate(nowdate())
    stale_cutoff = getdate(add_days(today, -STALE_LEAD_DAYS))
    conversation_for_inquiry = _conversation_by_inquiry(conversations)
    conversation_for_applicant = {
        clean(row.get("student_applicant")): row for row in conversations if clean(row.get("student_applicant"))
    }

    for row in conversations:
        dto = _conversation_dto(row)
        if _as_bool(row.get("needs_reply")) and clean(row.get("status")) == "Open":
            _append_queue_row(queues, "needs_reply", dto, limit=limit)
        if not clean(row.get("assigned_to")) and clean(row.get("status")) == "Open":
            _append_queue_row(queues, "unassigned", dto, limit=limit)
        if clean(row.get("external_identity")) and clean(row.get("identity_match_status")) != "Confirmed":
            _append_queue_row(queues, "unmatched_messages", dto, limit=limit)

    for row in inquiries:
        dto = _inquiry_dto(row, conversation_for_inquiry.get(clean(row.get("name"))))
        if not clean(row.get("assigned_to")) and clean(row.get("workflow_state")) in {"New", "Assigned"}:
            _append_queue_row(queues, "unassigned", dto, limit=limit)

        first_contact_due = getdate(row.get("first_contact_due_on")) if row.get("first_contact_due_on") else None
        followup_due = getdate(row.get("followup_due_on")) if row.get("followup_due_on") else None
        if _active_first_contact_state(row) and first_contact_due and first_contact_due < today:
            _append_queue_row(queues, "overdue_first_contact", dto, limit=limit)
        if (first_contact_due and first_contact_due == today) or (followup_due and followup_due == today):
            _append_queue_row(queues, "due_today", dto, limit=limit)
        if clean(row.get("workflow_state")) == "Qualified" and not clean(row.get("student_applicant")):
            _append_queue_row(queues, "qualified_not_invited", dto, limit=limit)
        modified_date = getdate(row.get("modified")) if row.get("modified") else None
        if (
            clean(row.get("workflow_state")) in {"New", "Assigned", "Contacted"}
            and modified_date
            and modified_date <= stale_cutoff
        ):
            _append_queue_row(queues, "stale_leads", dto, limit=limit)

    for row in applicants:
        conversation = conversation_for_applicant.get(clean(row.get("name")))
        dto = _applicant_dto(row, conversation)
        if clean(row.get("application_status")) == "Invited":
            _append_queue_row(queues, "invited_not_started", dto, limit=limit)
        if clean(row.get("application_status")) == "Missing Info":
            _append_queue_row(queues, "missing_documents", dto, limit=limit)

    return list(queues.values())


@frappe.whitelist()
def get_admissions_inbox_context(
    *,
    organization: str | None = None,
    school: str | None = None,
    limit: int | str | None = None,
) -> dict:
    user = ensure_admissions_crm_permission()
    resolved_limit = _bounded_limit(limit)
    scope = _resolve_scope(user, organization=organization, school=school)

    conversations = _fetch_conversation_rows(scope=scope, limit=resolved_limit)
    inquiries = _fetch_inquiry_rows(scope=scope, limit=resolved_limit)
    applicants = _fetch_applicant_rows(scope=scope, limit=resolved_limit)

    return {
        "ok": True,
        "generated_at": _as_text(now_datetime()),
        "filters": {
            "organization": scope.get("organization") or None,
            "school": scope.get("school") or None,
            "limit": resolved_limit,
        },
        "queues": _build_queues(
            conversations=conversations,
            inquiries=inquiries,
            applicants=applicants,
            limit=resolved_limit,
        ),
        "sources": {
            "crm_conversations": len(conversations),
            "inquiries": len(inquiries),
            "student_applicants": len(applicants),
            "org_communication_applicant_messages": 0,
        },
    }
