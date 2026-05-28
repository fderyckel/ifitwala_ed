from __future__ import annotations

from collections import OrderedDict

from frappe import _
from frappe.utils import add_days, getdate, nowdate

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.api.inbox.constants import QUEUE_IDS, STALE_LEAD_DAYS
from ifitwala_ed.admission.api.inbox.dto import (
    _applicant_dto,
    _applicant_message_dto,
    _as_bool,
    _conversation_dto,
    _inquiry_dto,
)
from ifitwala_ed.admission.api.inbox.queries import _conversation_by_inquiry


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
    *,
    conversations: list[dict],
    inquiries: list[dict],
    applicants: list[dict],
    applicant_case_summaries: dict[str, dict],
    limit: int,
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
        conversation_next_action = getdate(row.get("next_action_on")) if row.get("next_action_on") else None
        if conversation_next_action and conversation_next_action == today and not clean(row.get("inquiry")):
            _append_queue_row(queues, "due_today", dto, limit=limit)
        if clean(row.get("external_identity")) and clean(row.get("identity_match_status")) != "Confirmed":
            _append_queue_row(queues, "unmatched_messages", dto, limit=limit)

    for row in inquiries:
        dto = _inquiry_dto(row, conversation_for_inquiry.get(clean(row.get("name"))))
        if not clean(row.get("assigned_to")) and clean(row.get("workflow_state")) in {"New", "Assigned"}:
            _append_queue_row(queues, "unassigned", dto, limit=limit)

        first_contact_due = getdate(row.get("first_contact_due_on")) if row.get("first_contact_due_on") else None
        followup_due = getdate(row.get("followup_due_on")) if row.get("followup_due_on") else None
        conversation = conversation_for_inquiry.get(clean(row.get("name")))
        conversation_next_action = (
            getdate(conversation.get("next_action_on")) if conversation and conversation.get("next_action_on") else None
        )
        if _active_first_contact_state(row) and first_contact_due and first_contact_due < today:
            _append_queue_row(queues, "overdue_first_contact", dto, limit=limit)
        if (
            (first_contact_due and first_contact_due == today)
            or (followup_due and followup_due == today)
            or (conversation_next_action and conversation_next_action == today)
        ):
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
        case_summary = applicant_case_summaries.get(clean(row.get("name"))) or {}
        dto = _applicant_dto(row, conversation, case_summary)
        if _as_bool(case_summary.get("needs_reply")):
            _append_queue_row(
                queues,
                "needs_reply",
                _applicant_message_dto(row, case_summary, conversation),
                limit=limit,
            )
        if clean(row.get("application_status")) == "Invited":
            _append_queue_row(queues, "invited_not_started", dto, limit=limit)
        if clean(row.get("application_status")) == "Missing Info":
            _append_queue_row(queues, "missing_documents", dto, limit=limit)

    return list(queues.values())
