from __future__ import annotations

import frappe

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.api.inbox.scope import _scope_values


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
    conditions = ["sa.application_status NOT IN ('Rejected', 'Withdrawn', 'Promoted')"]
    params = {"limit": limit * 4}
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
            sa.applicant_user,
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
