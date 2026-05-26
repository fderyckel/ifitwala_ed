# ifitwala_ed/admission/api/crm/guards.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.admissions_crm_permissions import (
    doc_is_in_admissions_crm_scope,
    is_admissions_crm_user,
)


def _require_doc_read(user: str, doctype: str, name: str | None):
    docname = clean(name)
    if not docname:
        return None
    doc = frappe.get_doc(doctype, docname)
    if not frappe.has_permission(doctype, ptype="read", doc=doc, user=user):
        frappe.throw(
            _("You do not have permission to use {doctype} {docname}.").format(
                doctype=doctype,
                docname=docname,
            ),
            frappe.PermissionError,
        )
    return doc


def _assert_scope_allowed(user: str, *, organization: str | None, school: str | None) -> None:
    if doc_is_in_admissions_crm_scope(user=user, organization=organization, school=school):
        return
    frappe.throw(_("You do not have permission for this admissions CRM scope."), frappe.PermissionError)


def _require_conversation_write(user: str, conversation: str):
    conversation_name = clean(conversation)
    if not conversation_name:
        frappe.throw(_("Admission Conversation is required."))
    doc = frappe.get_doc("Admission Conversation", conversation_name)
    if not frappe.has_permission("Admission Conversation", ptype="write", doc=doc, user=user):
        frappe.throw(_("You do not have permission to update this admissions conversation."), frappe.PermissionError)
    return doc


def _require_inquiry_write(user: str, inquiry: str):
    inquiry_name = clean(inquiry)
    if not inquiry_name:
        frappe.throw(_("Inquiry is required."))
    doc = frappe.get_doc("Inquiry", inquiry_name)
    if not frappe.has_permission("Inquiry", ptype="write", doc=doc, user=user):
        frappe.throw(_("You do not have permission to update this Inquiry."), frappe.PermissionError)
    return doc


def _validate_crm_assignee(*, user: str, assigned_to: str, organization: str | None, school: str | None) -> None:
    assignee = clean(assigned_to)
    if not assignee:
        frappe.throw(_("Assigned To is required."))
    enabled = frappe.db.get_value("User", assignee, "enabled")
    if not enabled:
        frappe.throw(_("Assigned To must be an enabled admissions CRM user."))
    if not is_admissions_crm_user(assignee):
        frappe.throw(_("Assigned To must have an admissions CRM role."))
    if not doc_is_in_admissions_crm_scope(user=assignee, organization=organization, school=school):
        frappe.throw(_("Assigned To is outside this admissions CRM scope."))
    _assert_scope_allowed(user, organization=organization, school=school)
