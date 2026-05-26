# ifitwala_ed/admission/api/portal/enrollment.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.api.portal.access import _as_text, _ensure_applicant_match, _require_admissions_applicant
from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
    get_applicant_enrollment_choice_state,
    get_deposit_invoice_status_for_plan,
    get_latest_applicant_enrollment_plan,
)

PORTAL_STATUS_MAP = {
    "Draft": "Draft",
    "Invited": "Draft",
    "In Progress": "In Progress",
    "Missing Info": "Action Required",
    "Submitted": "In Review",
    "Under Review": "In Review",
    "Approved": "Accepted",
    "Rejected": "Rejected",
    "Withdrawn": "Withdrawn",
    "Promoted": "Completed",
}

PORTAL_EDITABLE_STATUSES = {"Invited", "In Progress", "Missing Info"}

READ_ONLY_REASON_MAP = {
    "Draft": _("Application not yet open."),
    "Submitted": _("Application submitted."),
    "Under Review": _("Application under review."),
    "Approved": _("Application accepted."),
    "Rejected": _("Application rejected."),
    "Withdrawn": _("Application withdrawn."),
    "Promoted": _("Application completed."),
}


def _empty_applicant_enrollment_choice_state(message: str | None = None) -> dict:
    return {
        "plan": None,
        "summary": {
            "has_plan": False,
            "has_courses": False,
            "has_selectable_courses": False,
            "can_edit_choices": False,
            "ready_for_offer_response": True,
            "required_course_count": 0,
            "optional_course_count": 0,
            "selected_optional_count": 0,
            "message": message or "",
        },
        "validation": {
            "status": None,
            "ready_for_offer_response": True,
            "reasons": [],
            "violations": [],
            "missing_required_courses": [],
            "ambiguous_courses": [],
            "group_summary": {},
        },
        "required_basket_groups": [],
        "courses": [],
    }


def _serialize_enrollment_offer(plan) -> dict | None:
    if not plan:
        return None
    status = _as_text(plan.get("status")).strip()
    choice_state = get_applicant_enrollment_choice_state(plan)
    choice_summary = choice_state.get("summary") or {}
    choice_validation = choice_state.get("validation") or {}
    return {
        "name": _as_text(plan.get("name")).strip(),
        "status": status,
        "academic_year": _as_text(plan.get("academic_year")).strip(),
        "term": _as_text(plan.get("term")).strip(),
        "program": _as_text(plan.get("program")).strip(),
        "program_offering": _as_text(plan.get("program_offering")).strip(),
        "offer_expires_on": _as_text(plan.get("offer_expires_on")).strip(),
        "offer_sent_on": _as_text(plan.get("offer_sent_on")).strip(),
        "offer_accepted_on": _as_text(plan.get("offer_accepted_on")).strip(),
        "offer_declined_on": _as_text(plan.get("offer_declined_on")).strip(),
        "offer_message": _as_text(plan.get("offer_message")).strip(),
        "can_accept": status == "Offer Sent",
        "can_decline": status == "Offer Sent",
        "course_choices_available": bool(choice_summary.get("has_courses")),
        "course_choices_can_edit": bool(choice_summary.get("can_edit_choices")),
        "course_choices_ready": bool(choice_validation.get("ready_for_offer_response")),
        "course_choice_blocking_reasons": list(choice_validation.get("reasons") or []),
        "course_choice_optional_count": cint(choice_summary.get("optional_course_count") or 0),
        "course_choice_selected_optional_count": cint(choice_summary.get("selected_optional_count") or 0),
        "deposit": get_deposit_invoice_status_for_plan(plan),
    }


def _portal_status_for(application_status: str, enrollment_offer: dict | None = None) -> str:
    offer_status = _as_text((enrollment_offer or {}).get("status")).strip()
    if application_status == "Approved":
        if offer_status == "Offer Sent":
            return "Offer Sent"
        if offer_status == "Offer Accepted":
            return "Accepted"
        if offer_status == "Offer Declined":
            return "Declined"
        if offer_status == "Offer Expired":
            return "Offer Expired"
        return "In Review"
    if application_status not in PORTAL_STATUS_MAP:
        frappe.throw(
            _("Invalid Application Status: {application_status}.").format(application_status=application_status)
        )
    return PORTAL_STATUS_MAP[application_status]


def _read_only_for(application_status: str, enrollment_offer: dict | None = None) -> tuple[bool, str | None]:
    if application_status in PORTAL_EDITABLE_STATUSES:
        return False, None
    offer_status = _as_text((enrollment_offer or {}).get("status")).strip()
    if application_status == "Approved":
        if offer_status == "Offer Sent":
            return True, _("Review your enrollment offer below.")
        if offer_status == "Offer Accepted":
            return True, _("Offer accepted.")
        if offer_status == "Offer Declined":
            return True, _("Offer declined.")
        if offer_status == "Offer Expired":
            return True, _("Offer expired.")
        return True, _("Admissions decision is being finalized.")
    return True, READ_ONLY_REASON_MAP.get(application_status) or _("Application is read-only.")


def get_applicant_enrollment_choices_impl(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    plan = get_latest_applicant_enrollment_plan(row.get("name"))
    if not plan:
        return _empty_applicant_enrollment_choice_state(
            _("Course choices will appear once admissions sends your enrollment offer.")
        )

    payload = get_applicant_enrollment_choice_state(plan)
    summary = payload.get("summary") or {}
    summary["message"] = (
        _("No program-offering courses are configured for this offer.") if not summary.get("has_courses") else ""
    )
    payload["summary"] = summary
    return payload


def update_applicant_enrollment_choices_impl(*, student_applicant: str | None = None, courses=None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    plan = get_latest_applicant_enrollment_plan(row.get("name"))
    if not plan:
        frappe.throw(_("No enrollment plan is available."))

    parsed_courses = frappe.parse_json(courses) if courses is not None else []
    if parsed_courses is None:
        parsed_courses = []
    if not isinstance(parsed_courses, list):
        frappe.throw(_("Courses payload must be a list."))

    payload = plan.update_portal_choices(user=user, courses=parsed_courses)
    return {"ok": True, **payload}


def accept_enrollment_offer_impl(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    plan = get_latest_applicant_enrollment_plan(
        row.get("name"),
        statuses={"Offer Sent", "Offer Accepted"},
    )
    if not plan:
        frappe.throw(_("No active enrollment offer is available."))

    result = plan.accept_offer(user=user)
    plan.reload()
    return {"ok": True, "result": result, "enrollment_offer": _serialize_enrollment_offer(plan)}


def decline_enrollment_offer_impl(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    plan = get_latest_applicant_enrollment_plan(
        row.get("name"),
        statuses={"Offer Sent", "Offer Declined"},
    )
    if not plan:
        frappe.throw(_("No active enrollment offer is available."))

    result = plan.decline_offer(user=user)
    plan.reload()
    return {"ok": True, "result": result, "enrollment_offer": _serialize_enrollment_offer(plan)}
