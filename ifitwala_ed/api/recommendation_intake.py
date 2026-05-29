# ifitwala_ed/api/recommendation_intake.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.api import recommendation_intake as _impl

get_recommendation_template_rows_for_applicant = _impl.get_recommendation_template_rows_for_applicant
get_recommendation_status_batch_for_applicants = _impl.get_recommendation_status_batch_for_applicants
get_recommendation_status_for_applicant = _impl.get_recommendation_status_for_applicant


def __getattr__(name: str):
    return getattr(_impl, name)


@frappe.whitelist()
def list_recommendation_templates(*, student_applicant: str | None = None):
    return _impl.list_recommendation_templates(student_applicant=student_applicant)


@frappe.whitelist()
def create_recommendation_request(payload=None, **kwargs):
    return _impl.create_recommendation_request(payload=payload, **kwargs)


@frappe.whitelist()
def resend_recommendation_request(
    *,
    recommendation_request: str | None = None,
    expires_in_days: int | None = None,
):
    return _impl.resend_recommendation_request(
        recommendation_request=recommendation_request,
        expires_in_days=expires_in_days,
    )


@frappe.whitelist()
def revoke_recommendation_request(*, recommendation_request: str | None = None):
    return _impl.revoke_recommendation_request(recommendation_request=recommendation_request)


@frappe.whitelist()
def list_recommendation_requests(*, student_applicant: str | None = None):
    return _impl.list_recommendation_requests(student_applicant=student_applicant)


@frappe.whitelist()
def get_recommendation_request_summary(*, student_applicant: str | None = None):
    return _impl.get_recommendation_request_summary(student_applicant=student_applicant)


@frappe.whitelist()
def get_recommendation_review_payload(
    *,
    student_applicant: str | None = None,
    recommendation_request: str | None = None,
    recommendation_submission: str | None = None,
    applicant_document_item: str | None = None,
):
    return _impl.get_recommendation_review_payload(
        student_applicant=student_applicant,
        recommendation_request=recommendation_request,
        recommendation_submission=recommendation_submission,
        applicant_document_item=applicant_document_item,
    )


@frappe.whitelist(allow_guest=True)
def get_recommendation_intake_payload(*, token: str | None = None):
    return _impl.get_recommendation_intake_payload(token=token)


@frappe.whitelist(allow_guest=True)
def send_recommendation_otp(*, token: str | None = None):
    return _impl.send_recommendation_otp(token=token)


@frappe.whitelist(allow_guest=True)
def verify_recommendation_otp(*, token: str | None = None, otp_code: str | None = None):
    return _impl.verify_recommendation_otp(token=token, otp_code=otp_code)


@frappe.whitelist(allow_guest=True)
def submit_recommendation(payload=None, **kwargs):
    return _impl.submit_recommendation(payload=payload, **kwargs)
