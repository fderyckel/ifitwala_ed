from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.api.communication.admin_context import _administrator_context_preserving_request_session
from ifitwala_ed.admission.api.communication.constants import (
    THREAD_COMMUNICATION_TYPE,
    THREAD_INTERACTION_MODE,
    THREAD_PORTAL_SURFACE,
    THREAD_STATUS,
)
from ifitwala_ed.admission.api.communication.context import _to_text


def _next_thread_title(context_doctype: str, context_name: str) -> str:
    base = f"Admissions Thread - {context_doctype} - {context_name}"
    candidate = base
    counter = 1
    while frappe.db.exists("Org Communication", {"title": candidate}):
        counter += 1
        candidate = f"{base} #{counter}"
    return candidate


def _get_thread_name(context_doctype: str, context_name: str) -> str | None:
    rows = frappe.get_all(
        "Org Communication",
        filters={
            "admission_context_doctype": context_doctype,
            "admission_context_name": context_name,
        },
        fields=["name"],
        order_by="creation asc",
        limit=1,
    )
    if not rows:
        return None
    return _to_text(rows[0].get("name")) or None


def _create_thread(*, context_doctype: str, context_name: str, context_row: dict) -> str:
    organization = _to_text(context_row.get("organization"))
    school = _to_text(context_row.get("school"))
    if not organization:
        frappe.throw(_("Student Applicant is missing organization; cannot create admissions communication thread."))
    if not school:
        frappe.throw(_("Student Applicant is missing school; cannot create admissions communication thread."))

    doc = frappe.new_doc("Org Communication")
    doc.title = _next_thread_title(context_doctype, context_name)
    doc.communication_type = THREAD_COMMUNICATION_TYPE
    doc.status = THREAD_STATUS
    doc.priority = "Normal"
    doc.organization = organization
    doc.school = school
    doc.portal_surface = THREAD_PORTAL_SURFACE
    doc.interaction_mode = THREAD_INTERACTION_MODE
    doc.allow_private_notes = 1
    doc.allow_public_thread = 1
    doc.admission_context_doctype = context_doctype
    doc.admission_context_name = context_name
    doc.message = _("Admissions case communication thread for {context_name}.").format(context_name=context_name)
    doc.insert(ignore_permissions=True)
    return doc.name


def _get_or_create_thread(*, context_doctype: str, context_name: str, context_row: dict) -> str:
    existing = _get_thread_name(context_doctype, context_name)
    if existing:
        return existing

    lock_key = f"admissions:thread:create:{context_doctype}:{context_name}"
    with frappe.cache().lock(lock_key, timeout=10):
        existing = _get_thread_name(context_doctype, context_name)
        if existing:
            return existing
        with _administrator_context_preserving_request_session():
            return _create_thread(
                context_doctype=context_doctype,
                context_name=context_name,
                context_row=context_row,
            )
