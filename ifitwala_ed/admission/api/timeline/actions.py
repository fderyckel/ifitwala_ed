from __future__ import annotations

from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.api.timeline.utils import _as_bool


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
