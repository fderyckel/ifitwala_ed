# ifitwala_ed/admission/api/portal/snapshot.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.api.portal.access import _as_text, _ensure_applicant_match, _require_admissions_applicant
from ifitwala_ed.admission.api.portal.enrollment import (
    PORTAL_EDITABLE_STATUSES,
    _portal_status_for,
    _serialize_enrollment_offer,
)
from ifitwala_ed.admission.api.portal.health import _portal_health_state
from ifitwala_ed.admission.api.portal.profile import _application_context_payload, _serialize_applicant_profile
from ifitwala_ed.admission.api.recommendation_intake import get_recommendation_status_for_applicant
from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
    get_latest_applicant_enrollment_plan,
)


def _completion_state_for_requirement(required: list, missing: list, unapproved: list | None = None) -> str:
    if not required:
        return "optional"
    missing = missing or []
    unapproved = unapproved or []
    if not missing and not unapproved:
        return "complete"
    if len(missing) < len(required) or unapproved:
        return "in_progress"
    return "pending"


def _completion_state_for_health(health: dict) -> str:
    if health.get("ok"):
        return "complete"
    if not bool(health.get("required_for_approval", True)):
        return "optional"
    status = (health.get("status") or "missing").strip()
    if status == "missing":
        return "pending"
    return "in_progress"


def _completion_state_for_interviews(interviews: dict) -> str:
    if interviews.get("ok"):
        return "complete"
    return "optional"


def _completion_state_for_recommendations(summary: dict) -> str:
    state = (summary or {}).get("state")
    if state in {"pending", "in_progress", "complete", "optional"}:
        return state

    required_total = max(0, cint((summary or {}).get("required_total") or 0))
    received_total = max(0, cint((summary or {}).get("received_total") or 0))
    if required_total <= 0:
        return "optional"
    if received_total >= required_total:
        return "complete"
    if received_total > 0:
        return "in_progress"
    return "pending"


def _derive_next_actions(application_status: str, readiness: dict, enrollment_offer: dict | None = None) -> list[dict]:
    actions: list[dict] = []
    offer_status = _as_text((enrollment_offer or {}).get("status")).strip()

    if offer_status == "Offer Sent":
        if not bool((enrollment_offer or {}).get("course_choices_ready", True)):
            actions.append(
                {
                    "label": _("Choose your courses"),
                    "route_name": "admissions-course-choices",
                    "intent": "primary",
                    "is_blocking": True,
                }
            )
        actions.append(
            {
                "label": _("Review and respond to your offer"),
                "route_name": "admissions-status",
                "intent": "secondary" if actions else "primary",
                "is_blocking": True,
            }
        )
        return actions

    if application_status not in PORTAL_EDITABLE_STATUSES:
        return actions

    policies = readiness.get("policies") or {}
    documents = readiness.get("documents") or {}
    health = readiness.get("health") or {}
    profile = readiness.get("profile") or {}
    recommendations = readiness.get("recommendations") or {}

    if not profile.get("ok"):
        actions.append(
            {
                "label": _("Complete profile information"),
                "route_name": "admissions-profile",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    if not policies.get("ok"):
        actions.append(
            {
                "label": _("Review required policies"),
                "route_name": "admissions-policies",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    if not documents.get("ok"):
        missing_docs = documents.get("missing") or []
        unapproved_docs = documents.get("unapproved") or []
        if missing_docs:
            actions.append(
                {
                    "label": _("Upload required documents"),
                    "route_name": "admissions-documents",
                    "intent": "primary",
                    "is_blocking": True,
                }
            )
        elif unapproved_docs:
            actions.append(
                {
                    "label": _("Documents under review"),
                    "route_name": "admissions-documents",
                    "intent": "default",
                    "is_blocking": False,
                }
            )

    if bool(health.get("required_for_approval", True)) and not health.get("ok"):
        actions.append(
            {
                "label": _("Complete health information"),
                "route_name": "admissions-health",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    required_recommendations = max(0, cint(recommendations.get("required_total") or 0))
    if required_recommendations > 0 and not recommendations.get("ok"):
        actions.append(
            {
                "label": _("Check recommendation status"),
                "route_name": "admissions-status",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    return actions


def get_applicant_snapshot_impl(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    latest_plan = get_latest_applicant_enrollment_plan(applicant.name)
    enrollment_offer = _serialize_enrollment_offer(latest_plan)
    readiness = applicant.get_readiness_snapshot()
    portal_health = _portal_health_state(applicant.name)
    health_required_for_approval = bool((readiness.get("health") or {}).get("required_for_approval", True))
    portal_health["required_for_approval"] = health_required_for_approval
    recommendation_status = get_recommendation_status_for_applicant(
        student_applicant=applicant.name,
        include_confidential=False,
    )
    readiness_for_portal = dict(readiness)
    readiness_for_portal["health"] = portal_health
    readiness_for_portal["recommendations"] = recommendation_status

    completeness = {
        "profile": _completion_state_for_requirement(
            (readiness.get("profile") or {}).get("required") or [],
            (readiness.get("profile") or {}).get("missing") or [],
        ),
        "health": _completion_state_for_health(portal_health),
        "documents": _completion_state_for_requirement(
            (readiness.get("documents") or {}).get("required") or [],
            (readiness.get("documents") or {}).get("missing") or [],
            (readiness.get("documents") or {}).get("unapproved") or [],
        ),
        "policies": _completion_state_for_requirement(
            (readiness.get("policies") or {}).get("required") or [],
            (readiness.get("policies") or {}).get("missing") or [],
        ),
        "interviews": _completion_state_for_interviews(readiness.get("interviews") or {}),
        "recommendations": _completion_state_for_recommendations(recommendation_status),
    }

    portal_status = _portal_status_for(applicant.application_status, enrollment_offer)
    next_actions = _derive_next_actions(applicant.application_status, readiness_for_portal, enrollment_offer)

    return {
        "applicant": {
            "name": applicant.name,
            "portal_status": portal_status,
            "submitted_at": applicant.get("submitted_at"),
            "decision_at": applicant.get("decision_at"),
        },
        "application_context": _application_context_payload(applicant),
        "profile": _serialize_applicant_profile(applicant),
        "completeness": completeness,
        "next_actions": next_actions,
        "enrollment_offer": enrollment_offer,
        "recommendations_summary": recommendation_status,
    }
