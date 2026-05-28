from __future__ import annotations

import frappe

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import (
    conversation_has_permission,
    doc_is_in_admissions_crm_scope,
)
from ifitwala_ed.admission.api.timeline.utils import _any_link_condition, _query_in_condition


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
