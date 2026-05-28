from __future__ import annotations

from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.api.timeline.constants import (
    APPROVED_APPLICANT_STATES,
    OFFER_ACCEPTED_PLAN_STATES,
    OFFER_SENT_PLAN_STATES,
    SUBMITTED_APPLICANT_STATES,
)
from ifitwala_ed.admission.api.timeline.utils import _as_bool


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
