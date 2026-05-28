from __future__ import annotations

from datetime import datetime

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import (
    conversation_has_permission,
    doc_is_in_admissions_crm_scope,
    ensure_admissions_crm_permission,
)
from ifitwala_ed.admission.api.communication.summaries import get_admissions_thread_summaries_for_applicants
from ifitwala_ed.admission.api.timeline.actions import _top_level_actions
from ifitwala_ed.admission.api.timeline.constants import TIMELINE_CONTEXT_DOCTYPES
from ifitwala_ed.admission.api.timeline.items import (
    _activity_items,
    _applicant_case_item,
    _applicant_item,
    _conversation_items,
    _inquiry_item,
    _message_items,
    _plan_items,
    _program_enrollment_items,
    _promotion_item,
    _request_items,
    _visit_items,
)
from ifitwala_ed.admission.api.timeline.queries import (
    _fetch_activities,
    _fetch_conversations,
    _fetch_enrollment_plans,
    _fetch_enrollment_requests,
    _fetch_messages,
    _fetch_program_enrollments,
    _fetch_visits,
)
from ifitwala_ed.admission.api.timeline.summary import _summary
from ifitwala_ed.admission.api.timeline.utils import _as_text, _bounded_limit, _strip_internal_fields


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


def get_admissions_timeline_context_impl(
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
