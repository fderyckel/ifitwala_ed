# ifitwala_ed/api/admissions_review.py

from __future__ import annotations

import frappe
from frappe import _


def _cache():
    return frappe.cache()


def _lock_key(*parts: str) -> str:
    cleaned = [str(part or "").strip() for part in parts if str(part or "").strip()]
    return "ifitwala_ed:lock:admissions_review:" + ":".join(cleaned)


def _idempotency_key(*parts: str) -> str:
    cleaned = [str(part or "").strip() for part in parts if str(part or "").strip()]
    return "ifitwala_ed:idempotency:admissions_review:" + ":".join(cleaned)


def _require_login() -> str:
    user = (frappe.session.user or "").strip()
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to continue."), frappe.PermissionError)
    return user


@frappe.whitelist()
def review_applicant_document_submission(
    *,
    student_applicant: str | None = None,
    applicant_document_item: str | None = None,
    decision: str | None = None,
    notes: str | None = None,
    client_request_id: str | None = None,
):
    user = _require_login()
    applicant_name = (student_applicant or "").strip()
    item_name = (applicant_document_item or "").strip()
    resolved_decision = (decision or "").strip()
    request_id = (client_request_id or "").strip() or None

    if not applicant_name:
        frappe.throw(_("Student Applicant is required."))
    if not item_name:
        frappe.throw(_("Submitted file is required."))

    lock_target = f"{applicant_name}:{item_name}:{resolved_decision}"
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key(user, lock_target, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key(user, lock_target), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        applicant_doc = frappe.get_doc("Student Applicant", applicant_name)
        response = applicant_doc.review_document_submission(
            applicant_document_item=item_name,
            decision=resolved_decision,
            notes=notes,
        )
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=60 * 10)
        return response


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
    user = _require_login()
    applicant_name = (student_applicant or "").strip()
    request_id = (client_request_id or "").strip() or None

    if not applicant_name:
        frappe.throw(_("Student Applicant is required."))

    document_anchor = (applicant_document or "").strip() or (document_type or "").strip() or "unscoped"
    override_value = (requirement_override or "").strip() or "clear"
    lock_target = f"{applicant_name}:{document_anchor}:{override_value}"
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key(user, lock_target, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key(user, lock_target), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        applicant_doc = frappe.get_doc("Student Applicant", applicant_name)
        response = applicant_doc.set_document_requirement_override(
            applicant_document=applicant_document,
            document_type=document_type,
            requirement_override=requirement_override,
            override_reason=override_reason,
        )
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=60 * 10)
        return response
