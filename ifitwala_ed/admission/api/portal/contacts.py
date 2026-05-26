# ifitwala_ed/admission/api/portal/contacts.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import (
    ensure_contact_dynamic_link,
    ensure_contact_for_email,
    normalize_email_value,
    upsert_contact_email,
)
from ifitwala_ed.admission.api.portal.access import _as_text
from ifitwala_ed.contacts.contact_privacy import get_raw_applicant_contact_prefill


def _get_inquiry_contact_for_applicant(applicant_doc) -> str | None:
    inquiry_name = (applicant_doc.get("inquiry") or "").strip()
    if not inquiry_name:
        return None
    contact_name = (frappe.db.get_value("Inquiry", inquiry_name, "contact") or "").strip()
    if contact_name and frappe.db.exists("Contact", contact_name):
        return contact_name
    return None


def _resolve_applicant_contact(
    applicant_doc,
    invite_email: str | None = None,
    *,
    allow_create: bool = False,
    bind_to_applicant: bool = False,
) -> str | None:
    contact_name = (applicant_doc.get("applicant_contact") or "").strip()
    if contact_name and not frappe.db.exists("Contact", contact_name):
        frappe.throw(_("Invalid Applicant Contact: {contact}").format(contact=contact_name))
    if not contact_name:
        contact_name = _get_inquiry_contact_for_applicant(applicant_doc) or ""

    invite_email = normalize_email_value(invite_email)
    if invite_email:
        existing_parent = frappe.db.get_value("Contact Email", {"email_id": invite_email}, "parent")
        if existing_parent and contact_name and existing_parent != contact_name:
            frappe.throw(_("Invite email is linked to a different Contact."))

        if not contact_name and allow_create:
            contact_name = ensure_contact_for_email(
                first_name=applicant_doc.get("first_name"),
                last_name=applicant_doc.get("last_name"),
                email=invite_email,
            )

        if contact_name:
            upsert_contact_email(contact_name, invite_email, set_primary_if_missing=True)

    if contact_name and bind_to_applicant:
        if (applicant_doc.get("applicant_contact") or "").strip() != contact_name:
            applicant_doc.flags.from_contact_sync = True
            applicant_doc.applicant_contact = contact_name
        ensure_contact_dynamic_link(
            contact_name=contact_name,
            link_doctype="Student Applicant",
            link_name=applicant_doc.name,
        )

    return contact_name or None


def _applicant_contact_prefill_payload(applicant) -> dict:
    contact_name = _as_text(_resolve_applicant_contact(applicant, allow_create=False)).strip()
    return get_raw_applicant_contact_prefill(
        student_applicant=applicant.name,
        contact=contact_name,
        purpose="applicant_contact_prefill",
    )
