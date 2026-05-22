from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime, strip_html

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import (
    conversation_has_permission,
    doc_is_in_admissions_crm_scope,
    ensure_admissions_crm_permission,
)
from ifitwala_ed.api.admissions_communication import get_admissions_thread_summaries_for_applicants

DEFAULT_LIMIT = 40
MAX_LIMIT = 100
TIMELINE_CONTEXT_DOCTYPES = {"Inquiry", "Student Applicant", "Admission Conversation"}
SUBMITTED_APPLICANT_STATES = {"Submitted", "Under Review", "Missing Info", "Approved", "Promoted"}
APPROVED_APPLICANT_STATES = {"Approved", "Promoted"}
OFFER_SENT_PLAN_STATES = {"Offer Sent", "Offer Accepted", "Hydrated"}
OFFER_ACCEPTED_PLAN_STATES = {"Offer Accepted", "Hydrated"}


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


def _preview(value: str | None, *, length: int = 180) -> str | None:
    text = " ".join(strip_html(value or "").split()).strip()
    if not text:
        return None
    if len(text) <= length:
        return text
    return f"{text[:length].rstrip()}..."


def _subtitle(parts: list[str | None]) -> str | None:
    cleaned = [clean(part) for part in parts if clean(part)]
    return " • ".join(cleaned) if cleaned else None


def _desk_url(doctype: str, name: str | None) -> str | None:
    docname = clean(name)
    if not docname:
        return None
    doctype_slug = doctype.strip().lower().replace(" ", "-")
    return f"/desk/{doctype_slug}/{quote(docname, safe='')}"


def _to_sort_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return get_datetime(value)
    except Exception:
        return None


def _item(
    *,
    kind: str,
    source_doctype: str,
    source_name: str,
    occurred_at: Any,
    title: str,
    summary: str | None = None,
    actor: str | None = None,
    visibility: str = "staff",
    context_labels: dict | None = None,
    open_url: str | None = None,
    actions: list[dict] | None = None,
) -> dict:
    occurred_text = _as_text(occurred_at)
    return {
        "id": f"{source_doctype.lower().replace(' ', '_')}:{source_name}:{kind}",
        "kind": kind,
        "source_doctype": source_doctype,
        "source_name": source_name,
        "occurred_at": occurred_text,
        "title": title,
        "summary": summary,
        "actor": clean(actor),
        "visibility": visibility,
        "context_labels": context_labels or {},
        "open_url": open_url,
        "actions": actions or [],
        "_sort_at": _to_sort_datetime(occurred_at),
    }


def _strip_internal_fields(items: list[dict]) -> list[dict]:
    for item in items:
        item.pop("_sort_at", None)
    return items


def _query_in_condition(field_sql: str, key: str, values: list[str], conditions: list[str], params: dict) -> None:
    cleaned = sorted({clean(value) for value in values if clean(value)})
    if not cleaned:
        conditions.append("1=0")
        return
    conditions.append(f"{field_sql} IN %({key})s")
    params[key] = tuple(cleaned)


def _any_link_condition(
    *,
    alias: str,
    context: dict,
    fields: dict[str, str],
    params: dict,
) -> str:
    parts: list[str] = []
    conversation_names = context.get("conversation_names") or []
    inquiry_names = context.get("inquiry_names") or []
    applicant_names = context.get("applicant_names") or []

    if fields.get("conversation") and conversation_names:
        key = f"{alias}_conversation_names"
        parts.append(f"{fields['conversation']} IN %({key})s")
        params[key] = tuple(sorted({clean(value) for value in conversation_names if clean(value)}))
    if fields.get("inquiry") and inquiry_names:
        key = f"{alias}_inquiry_names"
        parts.append(f"{fields['inquiry']} IN %({key})s")
        params[key] = tuple(sorted({clean(value) for value in inquiry_names if clean(value)}))
    if fields.get("student_applicant") and applicant_names:
        key = f"{alias}_applicant_names"
        parts.append(f"{fields['student_applicant']} IN %({key})s")
        params[key] = tuple(sorted({clean(value) for value in applicant_names if clean(value)}))

    return "(" + " OR ".join(parts) + ")" if parts else "1=0"


def _require_context_doc(user: str, doctype: str, name: str) -> dict:
    if doctype not in TIMELINE_CONTEXT_DOCTYPES:
        frappe.throw(_("Unsupported admissions timeline context: {doctype}.").format(doctype=doctype or _("(empty)")))
    if not clean(name):
        frappe.throw(_("context_name is required."))

    if doctype == "Admission Conversation":
        row = frappe.db.get_value(
            "Admission Conversation",
            name,
            [
                "name",
                "title",
                "organization",
                "school",
                "assigned_to",
                "status",
                "inquiry",
                "student_applicant",
                "needs_reply",
                "last_message_preview",
                "next_action_on",
                "latest_message_at",
                "last_activity_at",
                "creation",
                "modified",
            ],
            as_dict=True,
        )
        if not row:
            frappe.throw(_("Admission Conversation not found: {name}.").format(name=name))
        if not conversation_has_permission(dict(row), ptype="read", user=user):
            frappe.throw(_("You do not have permission to read this admissions conversation."), frappe.PermissionError)
        return {"doctype": doctype, **dict(row)}

    doc = frappe.get_doc(doctype, name)
    if not frappe.has_permission(doctype, ptype="read", doc=doc, user=user):
        frappe.throw(
            _("You do not have permission to read {doctype} {name}.").format(doctype=doctype, name=name),
            frappe.PermissionError,
        )

    fields = (
        [
            "name",
            "first_name",
            "last_name",
            "type_of_inquiry",
            "source",
            "message",
            "next_action_note",
            "submitted_at",
            "workflow_state",
            "archive_reason",
            "sla_status",
            "assigned_to",
            "organization",
            "school",
            "student_applicant",
            "first_contacted_at",
            "followup_due_on",
            "creation",
            "modified",
        ]
        if doctype == "Inquiry"
        else [
            "name",
            "title",
            "first_name",
            "last_name",
            "inquiry",
            "student",
            "applicant_user",
            "organization",
            "school",
            "program",
            "academic_year",
            "term",
            "program_offering",
            "application_status",
            "submitted_at",
            "decision_at",
            "creation",
            "modified",
        ]
    )
    row = {fieldname: doc.get(fieldname) for fieldname in fields}
    if not doc_is_in_admissions_crm_scope(
        user=user,
        organization=row.get("organization"),
        school=row.get("school"),
    ):
        frappe.throw(_("You do not have permission for this admissions CRM scope."), frappe.PermissionError)
    return {"doctype": doctype, **row}


def _fetch_related_inquiry(inquiry_name: str | None, user: str) -> dict | None:
    name = clean(inquiry_name)
    if not name:
        return None
    try:
        return _require_context_doc(user, "Inquiry", name)
    except frappe.PermissionError:
        raise
    except Exception:
        return None


def _fetch_related_applicant(applicant_name: str | None, user: str) -> dict | None:
    name = clean(applicant_name)
    if not name:
        return None
    try:
        return _require_context_doc(user, "Student Applicant", name)
    except frappe.PermissionError:
        raise
    except Exception:
        return None


def _context_label(row: dict) -> str:
    if row.get("doctype") == "Inquiry":
        parts = [clean(row.get("first_name")), clean(row.get("last_name"))]
        label = " ".join(part for part in parts if part)
        return label or clean(row.get("name")) or _("Inquiry")
    if row.get("doctype") == "Student Applicant":
        parts = [clean(row.get("first_name")), clean(row.get("last_name"))]
        label = clean(row.get("title")) or " ".join(part for part in parts if part)
        return label or clean(row.get("name")) or _("Student Applicant")
    return clean(row.get("title")) or clean(row.get("name")) or _("Admission Conversation")


def _resolve_context(user: str, context_doctype: str, context_name: str) -> dict:
    context_row = _require_context_doc(user, clean(context_doctype), clean(context_name))
    inquiry_row = context_row if context_row["doctype"] == "Inquiry" else None
    applicant_row = context_row if context_row["doctype"] == "Student Applicant" else None
    conversation_row = context_row if context_row["doctype"] == "Admission Conversation" else None

    if conversation_row:
        inquiry_row = _fetch_related_inquiry(conversation_row.get("inquiry"), user)
        applicant_row = _fetch_related_applicant(conversation_row.get("student_applicant"), user)
    elif inquiry_row:
        applicant_row = _fetch_related_applicant(inquiry_row.get("student_applicant"), user)
    elif applicant_row:
        inquiry_row = _fetch_related_inquiry(applicant_row.get("inquiry"), user)

    inquiry_names = [row.get("name") for row in (inquiry_row,) if row and clean(row.get("name"))]
    applicant_names = [row.get("name") for row in (applicant_row,) if row and clean(row.get("name"))]
    conversation_names = [row.get("name") for row in (conversation_row,) if row and clean(row.get("name"))]

    organization = clean(context_row.get("organization"))
    school = clean(context_row.get("school"))
    if not organization and inquiry_row:
        organization = clean(inquiry_row.get("organization"))
    if not school and inquiry_row:
        school = clean(inquiry_row.get("school"))
    if not organization and applicant_row:
        organization = clean(applicant_row.get("organization"))
    if not school and applicant_row:
        school = clean(applicant_row.get("school"))

    return {
        "requested": {"doctype": context_row["doctype"], "name": context_row["name"]},
        "label": _context_label(context_row),
        "organization": organization or None,
        "school": school or None,
        "inquiry": inquiry_row,
        "applicant": applicant_row,
        "conversation": conversation_row,
        "inquiry_names": inquiry_names,
        "applicant_names": applicant_names,
        "conversation_names": conversation_names,
    }


def _fetch_conversations(context: dict, user: str, limit: int) -> list[dict]:
    conditions = ["c.status != 'Spam'"]
    params = {"limit": limit}
    link_condition = _any_link_condition(
        alias="c",
        context=context,
        fields={"inquiry": "c.inquiry", "student_applicant": "c.student_applicant"},
        params=params,
    )
    exact_conversations = context.get("conversation_names") or []
    if exact_conversations:
        params["c_exact_conversations"] = tuple(sorted({clean(value) for value in exact_conversations if clean(value)}))
        conditions.append(f"({link_condition} OR c.name IN %(c_exact_conversations)s)")
    else:
        conditions.append(link_condition)

    rows = frappe.db.sql(
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
            c.needs_reply,
            c.last_message_preview,
            c.next_action_on,
            c.latest_message_at,
            c.last_activity_at,
            c.creation,
            c.modified
        FROM `tabAdmission Conversation` c
        WHERE {" AND ".join(f"({condition})" for condition in conditions)}
        ORDER BY COALESCE(c.latest_message_at, c.last_activity_at, c.modified, c.creation) DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )
    return [dict(row) for row in rows if conversation_has_permission(dict(row), ptype="read", user=user)]


def _fetch_messages(conversation_names: list[str], limit: int) -> list[dict]:
    conditions: list[str] = []
    params = {"limit": limit}
    _query_in_condition("m.conversation", "message_conversations", conversation_names, conditions, params)
    return frappe.db.sql(
        f"""
        SELECT
            m.name,
            m.conversation,
            m.organization,
            m.school,
            m.direction,
            m.message_type,
            m.body,
            m.message_at,
            m.delivery_status,
            m.linked_org_communication,
            m.linked_interaction_entry,
            m.linked_inquiry,
            m.linked_student_applicant,
            m.media_status,
            m.creation,
            m.modified
        FROM `tabAdmission Message` m
        WHERE {" AND ".join(f"({condition})" for condition in conditions)}
        ORDER BY COALESCE(m.message_at, m.creation) DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _fetch_activities(conversation_names: list[str], limit: int) -> list[dict]:
    conditions: list[str] = []
    params = {"limit": limit}
    _query_in_condition("a.conversation", "activity_conversations", conversation_names, conditions, params)
    return frappe.db.sql(
        f"""
        SELECT
            a.name,
            a.conversation,
            a.organization,
            a.school,
            a.inquiry,
            a.student_applicant,
            a.activity_type,
            a.activity_channel,
            a.outcome,
            a.note,
            a.next_action_on,
            a.staff_user,
            a.activity_at,
            a.creation,
            a.modified
        FROM `tabAdmission CRM Activity` a
        WHERE {" AND ".join(f"({condition})" for condition in conditions)}
        ORDER BY COALESCE(a.activity_at, a.creation) DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _fetch_visits(context: dict, user: str, limit: int) -> list[dict]:
    params = {"limit": limit}
    link_condition = _any_link_condition(
        alias="v",
        context=context,
        fields={"conversation": "v.conversation", "inquiry": "v.inquiry", "student_applicant": "v.student_applicant"},
        params=params,
    )
    rows = frappe.db.sql(
        f"""
        SELECT
            v.name,
            v.visit_title,
            v.organization,
            v.school,
            v.status,
            v.conversation,
            v.inquiry,
            v.student_applicant,
            v.visit_type,
            v.visit_mode,
            v.starts_on,
            v.ends_on,
            v.location,
            v.party_size,
            v.visitor_name,
            v.program_interest,
            v.lead_user,
            v.school_event,
            v.booked_crm_activity,
            v.attended_crm_activity,
            v.creation,
            v.modified
        FROM `tabAdmission Visit` v
        WHERE {link_condition}
        ORDER BY COALESCE(v.starts_on, v.creation) DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )
    return [
        dict(row)
        for row in rows
        if doc_is_in_admissions_crm_scope(
            user=user,
            organization=row.get("organization"),
            school=row.get("school"),
        )
    ]


def _fetch_enrollment_plans(applicant_names: list[str], limit: int) -> list[dict]:
    if not applicant_names:
        return []
    conditions: list[str] = []
    params = {"limit": limit}
    _query_in_condition("p.student_applicant", "plan_applicants", applicant_names, conditions, params)
    return frappe.db.sql(
        f"""
        SELECT
            p.name,
            p.student_applicant,
            p.student,
            p.organization,
            p.school,
            p.academic_year,
            p.term,
            p.program,
            p.program_offering,
            p.status,
            p.offer_expires_on,
            p.offer_sent_on,
            p.offer_accepted_on,
            p.deposit_required,
            p.deposit_amount,
            p.deposit_due_date,
            p.deposit_invoice,
            p.program_enrollment_request,
            p.hydrated_on,
            p.hydrated_by,
            p.creation,
            p.modified
        FROM `tabApplicant Enrollment Plan` p
        WHERE {" AND ".join(f"({condition})" for condition in conditions)}
        ORDER BY COALESCE(p.hydrated_on, p.offer_accepted_on, p.offer_sent_on, p.modified, p.creation) DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _fetch_enrollment_requests(applicant_names: list[str], plan_names: list[str], limit: int) -> list[dict]:
    if not applicant_names and not plan_names:
        return []
    conditions: list[str] = []
    params = {"limit": limit}
    parts: list[str] = []
    if applicant_names:
        params["request_applicants"] = tuple(sorted({clean(value) for value in applicant_names if clean(value)}))
        parts.append("r.source_student_applicant IN %(request_applicants)s")
    if plan_names:
        params["request_plans"] = tuple(sorted({clean(value) for value in plan_names if clean(value)}))
        parts.append("r.source_applicant_enrollment_plan IN %(request_plans)s")
    conditions.append("(" + " OR ".join(parts) + ")")
    return frappe.db.sql(
        f"""
        SELECT
            r.name,
            r.student,
            r.program_offering,
            r.request_kind,
            r.program,
            r.school,
            r.academic_year,
            r.status,
            r.source_student_applicant,
            r.source_applicant_enrollment_plan,
            r.creation,
            r.modified
        FROM `tabProgram Enrollment Request` r
        WHERE {" AND ".join(f"({condition})" for condition in conditions)}
        ORDER BY COALESCE(r.modified, r.creation) DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _fetch_program_enrollments(request_names: list[str], limit: int) -> list[dict]:
    if not request_names:
        return []
    conditions: list[str] = []
    params = {"limit": limit}
    _query_in_condition("e.program_enrollment_request", "enrollment_requests", request_names, conditions, params)
    return frappe.db.sql(
        f"""
        SELECT
            e.name,
            e.student,
            e.program,
            e.academic_year,
            e.enrollment_date,
            e.school,
            e.archived,
            e.program_offering,
            e.program_enrollment_request,
            e.enrollment_source,
            e.creation,
            e.modified
        FROM `tabProgram Enrollment` e
        WHERE {" AND ".join(f"({condition})" for condition in conditions)}
        ORDER BY COALESCE(e.enrollment_date, e.modified, e.creation) DESC
        LIMIT %(limit)s
        """,
        params,
        as_dict=True,
    )


def _context_labels(context: dict, **extra) -> dict:
    labels = {
        "organization": context.get("organization"),
        "school": context.get("school"),
        "inquiry": (context.get("inquiry") or {}).get("name"),
        "student_applicant": (context.get("applicant") or {}).get("name"),
    }
    for key, value in extra.items():
        if clean(value):
            labels[key] = value
    return {key: value for key, value in labels.items() if clean(value)}


def _conversation_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        status = clean(row.get("status"))
        title = _("Admissions conversation opened")
        if status in {"Closed", "Archived"}:
            title = _("Admissions conversation {status}").format(status=status.lower())
        items.append(
            _item(
                kind="touchpoint",
                source_doctype="Admission Conversation",
                source_name=row["name"],
                occurred_at=row.get("creation"),
                title=title,
                summary=_preview(row.get("last_message_preview")),
                actor=clean(row.get("assigned_to")),
                context_labels=_context_labels(
                    context,
                    conversation=row.get("name"),
                    status=row.get("status"),
                ),
                open_url=_desk_url("Admission Conversation", row.get("name")),
                actions=[{"id": "open_conversation", "label": _("Open Conversation"), "enabled": True}],
            )
        )
    return items


def _inquiry_item(row: dict | None, context: dict) -> list[dict]:
    if not row:
        return []
    title = _("Inquiry captured")
    if clean(row.get("workflow_state")) == "Archived":
        title = _("Inquiry archived")
    summary = _subtitle(
        [clean(row.get("workflow_state")), clean(row.get("type_of_inquiry")), _preview(row.get("message"))]
    )
    return [
        _item(
            kind="intake",
            source_doctype="Inquiry",
            source_name=row["name"],
            occurred_at=row.get("submitted_at") or row.get("creation"),
            title=title,
            summary=summary,
            actor=clean(row.get("assigned_to")),
            context_labels=_context_labels(context),
            open_url=_desk_url("Inquiry", row.get("name")),
            actions=[{"id": "open_inquiry", "label": _("Open Inquiry"), "enabled": True}],
        )
    ]


def _applicant_item(row: dict | None, context: dict) -> list[dict]:
    if not row:
        return []
    status = clean(row.get("application_status"))
    return [
        _item(
            kind="applicant",
            source_doctype="Student Applicant",
            source_name=row["name"],
            occurred_at=row.get("submitted_at") or row.get("creation"),
            title=_("Applicant {status}").format(status=status.lower() if status else _("created")),
            summary=_subtitle([status, clean(row.get("program")), clean(row.get("academic_year"))]),
            context_labels=_context_labels(context),
            open_url=_desk_url("Student Applicant", row.get("name")),
            actions=[{"id": "open_applicant", "label": _("Open Applicant"), "enabled": True}],
        )
    ]


def _message_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        direction = clean(row.get("direction"))
        message_type = clean(row.get("message_type")) or _("message")
        title = _("Inbound message") if direction == "Inbound" else _("Outbound message")
        if direction == "System":
            title = _("System message")
        items.append(
            _item(
                kind="message",
                source_doctype="Admission Message",
                source_name=row["name"],
                occurred_at=row.get("message_at") or row.get("creation"),
                title=title,
                summary=_subtitle([message_type, _preview(row.get("body"))]),
                actor=direction,
                context_labels=_context_labels(
                    context,
                    conversation=row.get("conversation"),
                    inquiry=row.get("linked_inquiry"),
                    student_applicant=row.get("linked_student_applicant"),
                ),
                open_url=_desk_url("Admission Message", row.get("name")),
                actions=[{"id": "open_message", "label": _("Open Message"), "enabled": True}],
            )
        )
    return items


def _activity_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        activity_type = clean(row.get("activity_type")) or _("Touchpoint")
        items.append(
            _item(
                kind="touchpoint",
                source_doctype="Admission CRM Activity",
                source_name=row["name"],
                occurred_at=row.get("activity_at") or row.get("creation"),
                title=activity_type,
                summary=_subtitle(
                    [clean(row.get("activity_channel")), clean(row.get("outcome")), _preview(row.get("note"))]
                ),
                actor=clean(row.get("staff_user")),
                context_labels=_context_labels(
                    context,
                    conversation=row.get("conversation"),
                    inquiry=row.get("inquiry"),
                    student_applicant=row.get("student_applicant"),
                ),
                open_url=_desk_url("Admission CRM Activity", row.get("name")),
                actions=[{"id": "open_activity", "label": _("Open Activity"), "enabled": True}],
            )
        )
    return items


def _visit_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        items.append(
            _item(
                kind="visit",
                source_doctype="Admission Visit",
                source_name=row["name"],
                occurred_at=row.get("starts_on") or row.get("creation"),
                title=clean(row.get("visit_title")) or _("Admission visit"),
                summary=_subtitle(
                    [
                        clean(row.get("status")),
                        clean(row.get("visit_type")),
                        clean(row.get("visit_mode")),
                        clean(row.get("location")),
                    ]
                ),
                actor=clean(row.get("lead_user")),
                context_labels=_context_labels(
                    context,
                    conversation=row.get("conversation"),
                    inquiry=row.get("inquiry"),
                    student_applicant=row.get("student_applicant"),
                ),
                open_url=_desk_url("Admission Visit", row.get("name")),
                actions=[{"id": "open_visit", "label": _("Open Visit"), "enabled": True}],
            )
        )
    return items


def _applicant_case_item(applicant_row: dict | None, case_summary: dict, context: dict) -> list[dict]:
    if not applicant_row or not clean(case_summary.get("thread_name")):
        return []
    return [
        _item(
            kind="message",
            source_doctype="Org Communication",
            source_name=case_summary["thread_name"],
            occurred_at=case_summary.get("last_message_at") or applicant_row.get("modified"),
            title=_("Applicant case message"),
            summary=_preview(case_summary.get("last_message_preview")),
            actor=clean(case_summary.get("last_message_from")),
            context_labels=_context_labels(context, student_applicant=applicant_row.get("name")),
            open_url=_desk_url("Student Applicant", applicant_row.get("name")),
            actions=[{"id": "message_family", "label": _("Message Family"), "enabled": True}],
        )
    ]


def _plan_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        status = clean(row.get("status"))
        offer_at = (
            row.get("offer_accepted_on") or row.get("offer_sent_on") or row.get("modified") or row.get("creation")
        )
        items.append(
            _item(
                kind="offer",
                source_doctype="Applicant Enrollment Plan",
                source_name=row["name"],
                occurred_at=offer_at,
                title=_("Offer plan {status}").format(status=status.lower() if status else _("updated")),
                summary=_subtitle([status, clean(row.get("program_offering")), clean(row.get("academic_year"))]),
                actor=clean(row.get("hydrated_by")),
                context_labels=_context_labels(context, student_applicant=row.get("student_applicant")),
                open_url=_desk_url("Applicant Enrollment Plan", row.get("name")),
                actions=[{"id": "manage_offer", "label": _("Manage Offer"), "enabled": True}],
            )
        )
        if _as_bool(row.get("deposit_required")) or clean(row.get("deposit_invoice")):
            deposit_summary = (
                _("Deposit invoice linked") if clean(row.get("deposit_invoice")) else _("Deposit required")
            )
            items.append(
                _item(
                    kind="deposit",
                    source_doctype="Applicant Enrollment Plan",
                    source_name=row["name"],
                    occurred_at=row.get("deposit_due_date") or row.get("modified") or row.get("creation"),
                    title=_("Admissions deposit"),
                    summary=_subtitle([deposit_summary, _as_text(row.get("deposit_due_date"))]),
                    context_labels=_context_labels(context, student_applicant=row.get("student_applicant")),
                    open_url=_desk_url("Applicant Enrollment Plan", row.get("name")),
                    actions=[{"id": "check_deposit", "label": _("Check Deposit"), "enabled": True}],
                )
            )
    return items


def _request_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        items.append(
            _item(
                kind="enrollment",
                source_doctype="Program Enrollment Request",
                source_name=row["name"],
                occurred_at=row.get("modified") or row.get("creation"),
                title=_("Enrollment request {status}").format(status=clean(row.get("status")).lower()),
                summary=_subtitle(
                    [clean(row.get("request_kind")), clean(row.get("program")), clean(row.get("academic_year"))]
                ),
                context_labels=_context_labels(
                    context,
                    student_applicant=row.get("source_student_applicant"),
                ),
                open_url=_desk_url("Program Enrollment Request", row.get("name")),
                actions=[{"id": "open_enrollment_request", "label": _("Open Request"), "enabled": True}],
            )
        )
    return items


def _program_enrollment_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        archived = _as_bool(row.get("archived"))
        items.append(
            _item(
                kind="enrollment",
                source_doctype="Program Enrollment",
                source_name=row["name"],
                occurred_at=row.get("enrollment_date") or row.get("creation"),
                title=_("Program enrollment archived") if archived else _("Program enrollment active"),
                summary=_subtitle(
                    [clean(row.get("program")), clean(row.get("academic_year")), clean(row.get("enrollment_source"))]
                ),
                context_labels=_context_labels(context),
                open_url=_desk_url("Program Enrollment", row.get("name")),
                actions=[{"id": "open_enrollment", "label": _("Open Enrollment"), "enabled": True}],
            )
        )
    return items


def _promotion_item(applicant_row: dict | None, context: dict) -> list[dict]:
    if not applicant_row or not clean(applicant_row.get("student")):
        return []
    return [
        _item(
            kind="enrollment",
            source_doctype="Student Applicant",
            source_name=applicant_row["name"],
            occurred_at=applicant_row.get("decision_at")
            or applicant_row.get("modified")
            or applicant_row.get("creation"),
            title=_("Applicant promoted to student"),
            summary=clean(applicant_row.get("student")),
            context_labels=_context_labels(context, student_applicant=applicant_row.get("name")),
            open_url=_desk_url("Student Applicant", applicant_row.get("name")),
            actions=[{"id": "open_student", "label": _("Open Student"), "enabled": True}],
        )
    ]


def _ladder_step(step_id: str, label: str, state: str, source: str | None = None) -> dict:
    return {"id": step_id, "label": label, "state": state, "source": source}


def _completion_ladder(
    *,
    inquiry: dict | None,
    applicant: dict | None,
    plans: list[dict],
    requests: list[dict],
    enrollments: list[dict],
) -> list[dict]:
    applicant_status = clean((applicant or {}).get("application_status"))
    plan_states = {clean(row.get("status")) for row in plans if clean(row.get("status"))}
    has_offer_sent = any(row.get("offer_sent_on") for row in plans) or bool(plan_states & OFFER_SENT_PLAN_STATES)
    has_offer_accepted = any(row.get("offer_accepted_on") for row in plans) or bool(
        plan_states & OFFER_ACCEPTED_PLAN_STATES
    )
    deposit_ready = any(
        has_offer_accepted and (not _as_bool(row.get("deposit_required")) or clean(row.get("deposit_invoice")))
        for row in plans
    )
    promoted = bool(applicant and (applicant_status == "Promoted" or clean(applicant.get("student"))))
    has_enrollment_request = bool(requests)
    enrolled = any(not _as_bool(row.get("archived")) for row in enrollments)
    identity_upgraded = bool(
        enrolled and applicant and clean(applicant.get("applicant_user")) and clean(applicant.get("student"))
    )

    states = {
        "lead": bool(inquiry),
        "applicant": bool(applicant),
        "submitted": bool(
            applicant and (applicant.get("submitted_at") or applicant_status in SUBMITTED_APPLICANT_STATES)
        ),
        "approved": bool(applicant_status in APPROVED_APPLICANT_STATES),
        "offer_sent": has_offer_sent,
        "offer_accepted": has_offer_accepted,
        "deposit_ready": deposit_ready,
        "promoted": promoted,
        "enrollment_request": has_enrollment_request,
        "enrolled": enrolled,
        "identity_upgraded": identity_upgraded,
    }

    ordered = [
        ("lead", _("Lead"), inquiry.get("name") if inquiry else None),
        ("applicant", _("Applicant"), applicant.get("name") if applicant else None),
        ("submitted", _("Submitted"), applicant.get("name") if applicant else None),
        ("approved", _("Approved"), applicant.get("name") if applicant else None),
        ("offer_sent", _("Offer Sent"), plans[0].get("name") if plans else None),
        ("offer_accepted", _("Offer Accepted"), plans[0].get("name") if plans else None),
        ("deposit_ready", _("Deposit Ready"), plans[0].get("name") if plans else None),
        ("promoted", _("Promoted"), applicant.get("name") if applicant else None),
        ("enrollment_request", _("Enrollment Request"), requests[0].get("name") if requests else None),
        ("enrolled", _("Enrolled"), enrollments[0].get("name") if enrollments else None),
        ("identity_upgraded", _("Identity Upgraded"), applicant.get("student") if applicant else None),
    ]

    first_pending_found = False
    ladder = []
    for step_id, label, source in ordered:
        if states[step_id]:
            state = "done"
        elif not first_pending_found:
            state = "current"
            first_pending_found = True
        else:
            state = "pending"
        ladder.append(_ladder_step(step_id, label, state, source))
    return ladder


def _top_level_actions(context: dict, conversations: list[dict], plans: list[dict]) -> list[dict]:
    context_doctype = context["requested"]["doctype"]
    conversation = context.get("conversation") or (conversations[0] if conversations else None)
    inquiry = context.get("inquiry")
    applicant = context.get("applicant")
    conversation_name = clean((conversation or {}).get("name"))

    if context_doctype == "Inquiry" and inquiry:
        state = clean(inquiry.get("workflow_state"))
        return [
            {
                "id": "log_activity",
                "label": _("Log Activity"),
                "enabled": bool(conversation_name),
                "target": conversation_name,
                "disabled_reason": None
                if conversation_name
                else _("Log a message first so an admissions conversation exists for this activity."),
            },
            {"id": "log_message", "label": _("Log Message"), "enabled": True, "target": inquiry.get("name")},
            {"id": "schedule_visit", "label": _("Schedule Visit"), "enabled": True, "target": inquiry.get("name")},
            {
                "id": "invite_to_apply",
                "label": _("Invite to Apply"),
                "enabled": state == "Qualified" and not clean(inquiry.get("student_applicant")),
                "target": inquiry.get("name"),
                "disabled_reason": None
                if state == "Qualified" and not clean(inquiry.get("student_applicant"))
                else _("Qualify the inquiry before inviting the family to apply."),
            },
            {
                "id": "archive",
                "label": _("Archive"),
                "enabled": state != "Archived",
                "target": inquiry.get("name"),
            },
        ]

    if context_doctype == "Student Applicant" and applicant:
        approved = clean(applicant.get("application_status")) == "Approved"
        has_deposit = any(_as_bool(row.get("deposit_required")) or clean(row.get("deposit_invoice")) for row in plans)
        return [
            {"id": "open_timeline", "label": _("Open Timeline"), "enabled": True, "target": applicant.get("name")},
            {"id": "message_family", "label": _("Message Family"), "enabled": True, "target": applicant.get("name")},
            {
                "id": "log_activity",
                "label": _("Log Activity"),
                "enabled": bool(conversation_name),
                "target": conversation_name,
                "disabled_reason": None
                if conversation_name
                else _("Log a message first so an admissions conversation exists for this activity."),
            },
            {"id": "schedule_visit", "label": _("Schedule Visit"), "enabled": True, "target": applicant.get("name")},
            {"id": "manage_offer", "label": _("Manage Offer"), "enabled": True, "target": applicant.get("name")},
            {
                "id": "check_deposit",
                "label": _("Check Deposit"),
                "enabled": has_deposit,
                "target": plans[0].get("name") if plans else applicant.get("name"),
                "disabled_reason": None
                if has_deposit
                else _("No admissions deposit has been prepared for this applicant."),
            },
            {
                "id": "promote",
                "label": _("Promote"),
                "enabled": approved,
                "target": applicant.get("name"),
                "disabled_reason": None if approved else _("Approve the applicant before promotion."),
            },
        ]

    return [
        {
            "id": "log_activity",
            "label": _("Log Activity"),
            "enabled": bool(conversation_name),
            "target": conversation_name,
            "disabled_reason": None
            if conversation_name
            else _("Log a message first so an admissions conversation exists for this activity."),
        },
        {
            "id": "log_message",
            "label": _("Log Message"),
            "enabled": bool(conversation_name),
            "target": conversation_name,
            "disabled_reason": None
            if conversation_name
            else _("A conversation is required before logging this message from the conversation context."),
        },
        {"id": "schedule_visit", "label": _("Schedule Visit"), "enabled": True, "target": conversation_name},
        {
            "id": "archive",
            "label": _("Archive"),
            "enabled": clean((conversation or {}).get("status")) == "Open",
            "target": conversation_name,
        },
    ]


def _summary(
    *,
    items: list[dict],
    context: dict,
    case_summary: dict,
    conversations: list[dict],
    plans: list[dict],
    requests: list[dict],
    enrollments: list[dict],
) -> dict:
    counts = Counter(item["kind"] for item in items)
    latest = max((item.get("_sort_at") for item in items if item.get("_sort_at")), default=None)
    return {
        "headline": _("Admissions relationship timeline"),
        "latest_at": _as_text(latest),
        "needs_reply": _as_bool(case_summary.get("needs_reply"))
        or any(_as_bool(row.get("needs_reply")) for row in conversations),
        "counts": dict(counts),
        "completion_ladder": _completion_ladder(
            inquiry=context.get("inquiry"),
            applicant=context.get("applicant"),
            plans=plans,
            requests=requests,
            enrollments=enrollments,
        ),
    }


@frappe.whitelist()
def get_admissions_timeline_context(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    limit: int | str | None = None,
) -> dict:
    user = ensure_admissions_crm_permission()
    resolved_limit = _bounded_limit(limit)
    source_limit = resolved_limit + 1
    context = _resolve_context(user, clean(context_doctype), clean(context_name))

    conversations = _fetch_conversations(context=context, user=user, limit=source_limit)
    known_conversation_names = {clean(row.get("name")) for row in conversations if clean(row.get("name"))} | {
        clean(value) for value in context.get("conversation_names") or [] if clean(value)
    }
    context["conversation_names"] = sorted(known_conversation_names)

    messages = _fetch_messages(context["conversation_names"], source_limit) if context["conversation_names"] else []
    activities = _fetch_activities(context["conversation_names"], source_limit) if context["conversation_names"] else []
    visits = _fetch_visits(context, user, source_limit)
    plans = _fetch_enrollment_plans(context.get("applicant_names") or [], source_limit)
    plan_names = [clean(row.get("name")) for row in plans if clean(row.get("name"))]
    requests = _fetch_enrollment_requests(context.get("applicant_names") or [], plan_names, source_limit)
    request_names = [clean(row.get("name")) for row in requests if clean(row.get("name"))]
    enrollments = _fetch_program_enrollments(request_names, source_limit)

    applicant = context.get("applicant")
    case_summary = {}
    if applicant:
        case_summary = (
            get_admissions_thread_summaries_for_applicants(
                applicant_rows=[applicant],
                user=user,
            ).get(clean(applicant.get("name")))
            or {}
        )

    items: list[dict] = []
    items.extend(_inquiry_item(context.get("inquiry"), context))
    items.extend(_applicant_item(applicant, context))
    items.extend(_promotion_item(applicant, context))
    items.extend(_conversation_items(conversations, context))
    items.extend(_message_items(messages, context))
    items.extend(_activity_items(activities, context))
    items.extend(_visit_items(visits, context))
    items.extend(_applicant_case_item(applicant, case_summary, context))
    items.extend(_plan_items(plans, context))
    items.extend(_request_items(requests, context))
    items.extend(_program_enrollment_items(enrollments, context))

    items.sort(key=lambda item: item.get("_sort_at") or datetime.min, reverse=True)
    has_more = len(items) > resolved_limit
    visible_items = items[:resolved_limit]

    return {
        "ok": True,
        "generated_at": _as_text(now_datetime()),
        "context": {
            "doctype": context["requested"]["doctype"],
            "name": context["requested"]["name"],
            "label": context["label"],
            "organization": context.get("organization"),
            "school": context.get("school"),
            "inquiry": (context.get("inquiry") or {}).get("name"),
            "student_applicant": (context.get("applicant") or {}).get("name"),
            "conversation": (context.get("conversation") or {}).get("name"),
            "limit": resolved_limit,
        },
        "summary": _summary(
            items=visible_items,
            context=context,
            case_summary=case_summary,
            conversations=conversations,
            plans=plans,
            requests=requests,
            enrollments=enrollments,
        ),
        "items": _strip_internal_fields(visible_items),
        "actions": _top_level_actions(context, conversations, plans),
        "has_more": has_more,
        "sources": {
            "inquiries": 1 if context.get("inquiry") else 0,
            "student_applicants": 1 if applicant else 0,
            "admission_conversations": len(conversations),
            "admission_messages": len(messages),
            "admission_crm_activities": len(activities),
            "admission_visits": len(visits),
            "applicant_case_messages": 1 if clean(case_summary.get("thread_name")) else 0,
            "applicant_enrollment_plans": len(plans),
            "program_enrollment_requests": len(requests),
            "program_enrollments": len(enrollments),
        },
    }
