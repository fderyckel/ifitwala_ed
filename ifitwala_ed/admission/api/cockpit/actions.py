# ifitwala_ed/admission/api/cockpit/actions.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import has_scoped_staff_access_to_student_applicant
from ifitwala_ed.admission.api.cockpit.access import _ensure_cockpit_access, _to_text
from ifitwala_ed.admission.api.cockpit.cache import invalidate_admissions_cockpit_cache
from ifitwala_ed.admission.api.cockpit.urls import _doc_url


def _require_applicant_enrollment_plan_name(applicant_enrollment_plan: str) -> str:
    plan_name = _to_text(applicant_enrollment_plan)
    if not plan_name:
        frappe.throw(_("Applicant Enrollment Plan is required."))
    return plan_name


def _require_cockpit_student_applicant_name(student_applicant: str, *, user: str | None = None) -> str:
    applicant_name = _to_text(student_applicant)
    if not applicant_name:
        frappe.throw(_("Student Applicant is required."))

    resolved_user = user or _ensure_cockpit_access()
    if has_scoped_staff_access_to_student_applicant(
        user=resolved_user,
        student_applicant=applicant_name,
    ):
        return applicant_name

    frappe.throw(_("You do not have permission to access this applicant."), frappe.PermissionError)
    return applicant_name


def _require_cockpit_applicant_enrollment_plan_name(applicant_enrollment_plan: str) -> str:
    user = _ensure_cockpit_access()
    plan_name = _require_applicant_enrollment_plan_name(applicant_enrollment_plan)
    applicant_name = _to_text(frappe.db.get_value("Applicant Enrollment Plan", plan_name, "student_applicant"))
    if not applicant_name:
        frappe.throw(_("Applicant Enrollment Plan was not found."))
    _require_cockpit_student_applicant_name(applicant_name, user=user)
    return plan_name


def get_or_create_admissions_cockpit_offer_plan_impl(student_applicant: str):
    user = _ensure_cockpit_access()
    applicant_name = _require_cockpit_student_applicant_name(student_applicant, user=user)
    from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
        ensure_applicant_enrollment_plan,
        get_active_applicant_enrollment_plan_name,
    )

    existing_name = _to_text(get_active_applicant_enrollment_plan_name(applicant_name))
    plan = ensure_applicant_enrollment_plan(applicant_name)
    created = not bool(existing_name)
    if created:
        invalidate_admissions_cockpit_cache()

    return {
        "ok": True,
        "created": created,
        "student_applicant": applicant_name,
        "applicant_enrollment_plan": plan.name,
        "status": _to_text(plan.status) or "Draft",
        "open_url": _doc_url("Applicant Enrollment Plan", plan.name),
    }


def promote_admissions_cockpit_applicant_impl(student_applicant: str):
    user = _ensure_cockpit_access()
    applicant_name = _require_cockpit_student_applicant_name(student_applicant, user=user)
    applicant = frappe.get_doc("Student Applicant", applicant_name)

    student_name = _to_text(applicant.promote_to_student())
    applicant.reload()
    student_name = student_name or _to_text(applicant.student)
    invalidate_admissions_cockpit_cache()

    return {
        "ok": True,
        "student_applicant": applicant.name,
        "student": student_name or None,
        "status": _to_text(applicant.application_status),
        "open_url": _doc_url("Student", student_name) if student_name else None,
    }


def send_admissions_cockpit_offer_impl(applicant_enrollment_plan: str):
    plan_name = _require_cockpit_applicant_enrollment_plan_name(applicant_enrollment_plan)
    plan = frappe.get_doc("Applicant Enrollment Plan", plan_name)
    result = plan.send_offer() or {}
    invalidate_admissions_cockpit_cache()
    return {
        "ok": bool(result.get("ok")),
        "applicant_enrollment_plan": plan.name,
        "status": _to_text(result.get("status")) or _to_text(plan.status),
        "open_url": _doc_url("Applicant Enrollment Plan", plan.name),
    }


def hydrate_admissions_cockpit_request_impl(applicant_enrollment_plan: str):
    plan_name = _require_cockpit_applicant_enrollment_plan_name(applicant_enrollment_plan)
    from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
        hydrate_program_enrollment_request_from_applicant_plan,
    )

    result = hydrate_program_enrollment_request_from_applicant_plan(plan_name) or {}
    request_name = _to_text(result.get("name"))
    plan_status = _to_text(frappe.db.get_value("Applicant Enrollment Plan", plan_name, "status"))
    invalidate_admissions_cockpit_cache()
    return {
        "ok": True,
        "applicant_enrollment_plan": plan_name,
        "status": plan_status or "Hydrated",
        "program_enrollment_request": request_name or None,
        "program_enrollment_request_url": _doc_url("Program Enrollment Request", request_name)
        if request_name
        else None,
        "created": bool(result.get("created")),
    }


def generate_admissions_cockpit_deposit_invoice_impl(applicant_enrollment_plan: str):
    plan_name = _require_cockpit_applicant_enrollment_plan_name(applicant_enrollment_plan)
    from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
        generate_deposit_invoice_from_offer,
    )

    result = generate_deposit_invoice_from_offer(plan_name) or {}
    invalidate_admissions_cockpit_cache()
    return {
        "ok": bool(result.get("ok")),
        "created": bool(result.get("created")),
        "applicant_enrollment_plan": plan_name,
        "deposit": result.get("deposit") or {},
        "invoice": result.get("invoice") or {},
    }
