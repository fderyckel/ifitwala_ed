# ifitwala_ed/admission/api/review_endpoints.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.api.cockpit.cache import invalidate_admissions_cockpit_cache
from ifitwala_ed.admission.api.review import (
    review_applicant_document_submission_impl,
    set_document_requirement_override_impl,
)


@frappe.whitelist()
def review_applicant_document_submission(
    *,
    student_applicant: str | None = None,
    applicant_document_item: str | None = None,
    decision: str | None = None,
    notes: str | None = None,
    client_request_id: str | None = None,
):
    return review_applicant_document_submission_impl(
        student_applicant=student_applicant,
        applicant_document_item=applicant_document_item,
        decision=decision,
        notes=notes,
        client_request_id=client_request_id,
        invalidate_cache=invalidate_admissions_cockpit_cache,
    )


@frappe.whitelist()
def set_document_requirement_override(
    *,
    student_applicant: str | None = None,
    applicant_document: str | None = None,
    document_type: str | None = None,
    requirement_override: str | None = None,
    override_reason: str | None = None,
    client_request_id: str | None = None,
):
    return set_document_requirement_override_impl(
        student_applicant=student_applicant,
        applicant_document=applicant_document,
        document_type=document_type,
        requirement_override=requirement_override,
        override_reason=override_reason,
        client_request_id=client_request_id,
        invalidate_cache=invalidate_admissions_cockpit_cache,
    )


__all__ = [
    "review_applicant_document_submission",
    "set_document_requirement_override",
]
