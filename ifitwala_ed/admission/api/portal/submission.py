# ifitwala_ed/admission/api/portal/submission.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.api.portal.access import _ensure_applicant_match, _require_admissions_applicant


def submit_application_impl(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    result = applicant._submit_application(permission_checker=None)
    return {"ok": True, "changed": result.get("changed")}


def withdraw_application_impl(
    *,
    student_applicant: str | None = None,
    reason: str | None = None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    result = applicant.withdraw_application(reason=reason)
    return {"ok": True, "changed": result.get("changed")}
