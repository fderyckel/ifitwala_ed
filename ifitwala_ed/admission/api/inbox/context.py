from __future__ import annotations

from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import ensure_admissions_crm_permission
from ifitwala_ed.admission.api.communication.summaries import get_admissions_thread_summaries_for_applicants
from ifitwala_ed.admission.api.inbox.constants import DEFAULT_LIMIT, MAX_LIMIT
from ifitwala_ed.admission.api.inbox.dto import _as_text
from ifitwala_ed.admission.api.inbox.queries import (
    _fetch_applicant_rows,
    _fetch_conversation_rows,
    _fetch_inquiry_rows,
)
from ifitwala_ed.admission.api.inbox.queues import _build_queues
from ifitwala_ed.admission.api.inbox.scope import _resolve_scope


def _bounded_limit(value: int | str | None) -> int:
    limit = cint(value) or DEFAULT_LIMIT
    return min(max(limit, 1), MAX_LIMIT)


def get_admissions_inbox_context_impl(
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
    applicant_case_summaries = get_admissions_thread_summaries_for_applicants(
        applicant_rows=applicants,
        user=user,
    )

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
            applicant_case_summaries=applicant_case_summaries,
            limit=resolved_limit,
        ),
        "sources": {
            "crm_conversations": len(conversations),
            "inquiries": len(inquiries),
            "student_applicants": len(applicants),
            "org_communication_applicant_messages": sum(
                1 for summary in applicant_case_summaries.values() if clean(summary.get("thread_name"))
            ),
        },
    }
