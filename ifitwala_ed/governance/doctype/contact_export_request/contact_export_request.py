# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

ALLOWED_SCOPE_TYPES = frozenset(
    {
        "Student Group Guardians",
        "Admissions Applicants",
        "Inquiry Leads",
        "Employees",
    }
)
REJECTED_SCOPE_TYPES = frozenset(
    {
        "All Contacts",
        "All Guardians",
        "All Students",
        "All Applicants",
        "All Employees",
    }
)
VALID_STATUSES = frozenset({"Draft", "Submitted", "Approved", "Rejected", "Expired", "Used", "Cancelled"})


class ContactExportRequest(Document):
    def _from_contact_export_service(self) -> bool:
        flags = getattr(self, "flags", None)
        if hasattr(flags, "get"):
            return bool(flags.get("from_contact_export_service"))
        return bool(getattr(flags, "from_contact_export_service", False))

    def before_insert(self):
        if not self._from_contact_export_service():
            frappe.throw(
                _("Contact Export Request must be created by the contact export workflow."),
                frappe.PermissionError,
            )

    def before_save(self):
        if not self.is_new() and not self._from_contact_export_service():
            frappe.throw(
                _("Contact Export Request must be changed through the contact export workflow."),
                frappe.PermissionError,
            )

    def validate(self):
        self._validate_status()
        self._validate_required_fields()
        self._validate_scope()
        self._validate_approval_state()

    def before_delete(self):
        frappe.throw(_("Contact Export Request records cannot be deleted."))

    def _validate_status(self) -> None:
        if not (self.status or "").strip():
            self.status = "Draft"
        if self.status not in VALID_STATUSES:
            frappe.throw(_("Invalid Contact Export Request status."))

    def _validate_required_fields(self) -> None:
        if not (self.requester or "").strip():
            self.requester = frappe.session.user
        if not (self.purpose or "").strip():
            frappe.throw(_("Purpose is required for contact export requests."))
        if not (self.legal_basis or "").strip():
            frappe.throw(_("Legal basis is required for contact export requests."))

    def _validate_scope(self) -> None:
        scope_type = (self.scope_type or "").strip()
        if not scope_type:
            frappe.throw(_("Scope type is required for contact export requests."))
        if scope_type in REJECTED_SCOPE_TYPES or scope_type not in ALLOWED_SCOPE_TYPES:
            frappe.throw(_("Global contact export scopes are not allowed."))

        if scope_type == "Student Group Guardians" and not (self.scope_name or "").strip():
            frappe.throw(_("Student Group Guardians export requires a Student Group scope name."))

        if scope_type in {"Admissions Applicants", "Inquiry Leads", "Employees"}:
            has_scope = bool((self.organization or "").strip() or (self.school or "").strip())
            if not has_scope:
                frappe.throw(_("Contact export requires an Organization or School scope."))

    def _validate_approval_state(self) -> None:
        if self.status == "Approved":
            if not self._from_contact_export_service():
                frappe.throw(_("Contact export approval must use the governed workflow."), frappe.PermissionError)
            if not (self.approved_by or "").strip():
                frappe.throw(_("Approved contact export requests require an approver."))
            if not self.approved_on:
                frappe.throw(_("Approved contact export requests require an approval timestamp."))
            if not self.expires_on:
                frappe.throw(_("Approved contact export requests require an expiry timestamp."))
            if self.estimated_row_count in (None, ""):
                frappe.throw(_("Estimated row count is required before approval."))

        if self.status == "Rejected" and not (self.rejection_reason or "").strip():
            frappe.throw(_("Rejected contact export requests require a rejection reason."))
