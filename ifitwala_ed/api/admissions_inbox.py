from __future__ import annotations

import frappe

from ifitwala_ed.admission.api.communication.summaries import get_admissions_thread_summaries_for_applicants
from ifitwala_ed.admission.api.inbox.assignees import search_admissions_inbox_assignees_impl
from ifitwala_ed.admission.api.inbox.constants import DEFAULT_LIMIT, MAX_LIMIT, QUEUE_IDS, STALE_LEAD_DAYS
from ifitwala_ed.admission.api.inbox.context import _bounded_limit, get_admissions_inbox_context_impl
from ifitwala_ed.admission.api.inbox.dto import (
    _applicant_actions,
    _applicant_case_actions,
    _applicant_dto,
    _applicant_message_dto,
    _as_bool,
    _as_text,
    _base_row,
    _conversation_actions,
    _conversation_dto,
    _desk_url,
    _inquiry_actions,
    _inquiry_dto,
    _name_from_parts,
    _subtitle,
)
from ifitwala_ed.admission.api.inbox.queries import (
    _add_in_tuple_condition,
    _apply_scope_conditions,
    _conversation_by_inquiry,
    _fetch_applicant_rows,
    _fetch_conversation_rows,
    _fetch_inquiry_rows,
    _where_clause,
)
from ifitwala_ed.admission.api.inbox.queues import (
    _active_first_contact_state,
    _append_queue_row,
    _build_queues,
    _queue_label,
    _queue_shell,
)
from ifitwala_ed.admission.api.inbox.scope import (
    _descendant_organizations,
    _descendant_schools,
    _resolve_scope,
    _scope_values,
)

_INBOX_COMPAT_EXPORTS = (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    STALE_LEAD_DAYS,
    QUEUE_IDS,
    _bounded_limit,
    _as_text,
    _as_bool,
    _scope_values,
    _descendant_organizations,
    _descendant_schools,
    _resolve_scope,
    _add_in_tuple_condition,
    _apply_scope_conditions,
    _where_clause,
    _fetch_conversation_rows,
    _fetch_inquiry_rows,
    _fetch_applicant_rows,
    _conversation_by_inquiry,
    _name_from_parts,
    _subtitle,
    _base_row,
    _desk_url,
    _conversation_actions,
    _inquiry_actions,
    _applicant_actions,
    _applicant_case_actions,
    _conversation_dto,
    _inquiry_dto,
    _applicant_dto,
    _applicant_message_dto,
    _queue_shell,
    _queue_label,
    _append_queue_row,
    _active_first_contact_state,
    _build_queues,
    get_admissions_thread_summaries_for_applicants,
    search_admissions_inbox_assignees_impl,
)


@frappe.whitelist()
def get_admissions_inbox_context(
    *,
    organization: str | None = None,
    school: str | None = None,
    limit: int | str | None = None,
) -> dict:
    return get_admissions_inbox_context_impl(
        organization=organization,
        school=school,
        limit=limit,
    )


@frappe.whitelist()
def search_admissions_inbox_assignees(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    assignment_lane: str | None = None,
    query: str | None = None,
    limit: int | str | None = None,
) -> list[dict]:
    return search_admissions_inbox_assignees_impl(
        context_doctype=context_doctype,
        context_name=context_name,
        organization=organization,
        school=school,
        assignment_lane=assignment_lane,
        query=query,
        limit=limit,
    )
