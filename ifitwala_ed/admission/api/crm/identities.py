# ifitwala_ed/admission/api/crm/identities.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import ensure_admissions_crm_permission
from ifitwala_ed.admission.api.crm.guards import _require_doc_read
from ifitwala_ed.admission.api.crm.idempotency import IDEMPOTENCY_TTL_SECONDS, _cache, _idempotency_key, _lock_key


def confirm_admission_external_identity_impl(
    *,
    external_identity: str | None = None,
    contact: str | None = None,
    guardian: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    match_status: str | None = "Confirmed",
    client_request_id: str | None = None,
):
    user = ensure_admissions_crm_permission()
    identity_name = clean(external_identity)
    if not identity_name:
        frappe.throw(_("Admission External Identity is required."))

    request_id = clean(client_request_id)
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key("confirm_identity", user, identity_name, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key("confirm_identity", user, identity_name), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        identity_doc = _require_doc_read(user, "Admission External Identity", identity_name)
        if not frappe.has_permission("Admission External Identity", ptype="write", doc=identity_doc, user=user):
            frappe.throw(_("You do not have permission to update this external identity."), frappe.PermissionError)

        status_value = clean(match_status) or "Confirmed"
        if status_value not in {"Unmatched", "Suggested", "Confirmed", "Rejected"}:
            frappe.throw(_("Invalid match status: {status}.").format(status=status_value))

        if clean(contact):
            _require_doc_read(user, "Contact", contact)
            identity_doc.linked_contact = clean(contact)
        if clean(guardian):
            _require_doc_read(user, "Guardian", guardian)
            identity_doc.linked_guardian = clean(guardian)
        if clean(inquiry):
            _require_doc_read(user, "Inquiry", inquiry)
            identity_doc.linked_inquiry = clean(inquiry)
        if clean(student_applicant):
            _require_doc_read(user, "Student Applicant", student_applicant)
            identity_doc.linked_student_applicant = clean(student_applicant)

        identity_doc.match_status = status_value
        identity_doc.save(ignore_permissions=True)

        response = {
            "ok": True,
            "external_identity": {
                "name": identity_doc.name,
                "match_status": identity_doc.match_status,
                "linked_contact": identity_doc.linked_contact,
                "linked_guardian": identity_doc.linked_guardian,
                "linked_inquiry": identity_doc.linked_inquiry,
                "linked_student_applicant": identity_doc.linked_student_applicant,
            },
        }
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return response
