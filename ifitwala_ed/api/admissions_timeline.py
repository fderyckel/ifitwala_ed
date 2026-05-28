from __future__ import annotations

import frappe

from ifitwala_ed.admission.api.communication.summaries import get_admissions_thread_summaries_for_applicants
from ifitwala_ed.admission.api.timeline.actions import _top_level_actions
from ifitwala_ed.admission.api.timeline.constants import (
    APPROVED_APPLICANT_STATES,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    OFFER_ACCEPTED_PLAN_STATES,
    OFFER_SENT_PLAN_STATES,
    SUBMITTED_APPLICANT_STATES,
    TIMELINE_CONTEXT_DOCTYPES,
)
from ifitwala_ed.admission.api.timeline.context import (
    _context_label,
    _fetch_related_applicant,
    _fetch_related_inquiry,
    _require_context_doc,
    _resolve_context,
    get_admissions_timeline_context_impl,
)
from ifitwala_ed.admission.api.timeline.items import (
    _activity_items,
    _applicant_case_item,
    _applicant_item,
    _context_labels,
    _conversation_items,
    _inquiry_item,
    _message_items,
    _plan_items,
    _program_enrollment_items,
    _promotion_item,
    _request_items,
    _visit_items,
)
from ifitwala_ed.admission.api.timeline.ladder import _completion_ladder, _ladder_step
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
from ifitwala_ed.admission.api.timeline.utils import (
    _any_link_condition,
    _as_bool,
    _as_text,
    _bounded_limit,
    _desk_url,
    _item,
    _preview,
    _query_in_condition,
    _strip_internal_fields,
    _subtitle,
    _to_sort_datetime,
)

_TIMELINE_COMPAT_EXPORTS = (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    TIMELINE_CONTEXT_DOCTYPES,
    SUBMITTED_APPLICANT_STATES,
    APPROVED_APPLICANT_STATES,
    OFFER_SENT_PLAN_STATES,
    OFFER_ACCEPTED_PLAN_STATES,
    _bounded_limit,
    _as_text,
    _as_bool,
    _preview,
    _subtitle,
    _desk_url,
    _to_sort_datetime,
    _item,
    _strip_internal_fields,
    _query_in_condition,
    _any_link_condition,
    _require_context_doc,
    _fetch_related_inquiry,
    _fetch_related_applicant,
    _context_label,
    _resolve_context,
    _fetch_conversations,
    _fetch_messages,
    _fetch_activities,
    _fetch_visits,
    _fetch_enrollment_plans,
    _fetch_enrollment_requests,
    _fetch_program_enrollments,
    _context_labels,
    _conversation_items,
    _inquiry_item,
    _applicant_item,
    _message_items,
    _activity_items,
    _visit_items,
    _applicant_case_item,
    _plan_items,
    _request_items,
    _program_enrollment_items,
    _promotion_item,
    _ladder_step,
    _completion_ladder,
    _top_level_actions,
    _summary,
    get_admissions_thread_summaries_for_applicants,
)


@frappe.whitelist()
def get_admissions_timeline_context(
    *,
    context_doctype: str | None = None,
    context_name: str | None = None,
    limit: int | str | None = None,
) -> dict:
    return get_admissions_timeline_context_impl(
        context_doctype=context_doctype,
        context_name=context_name,
        limit=limit,
    )
