# ifitwala_ed/admission/doctype/applicant_document_item/applicant_document_item.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.admission.doctype.applicant_document.applicant_document import (
    sync_applicant_document_review_from_items,
)

UPLOAD_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", "Admissions Applicant"}
REVIEW_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager"}


class ApplicantDocumentItem(Document):
    def validate(self):
        before = self.get_doc_before_save() if not self.is_new() else None
        self._normalize_fields()
        self._validate_parent_document()
        self._validate_permissions(before)
        self._validate_applicant_state()
        self._validate_immutable_fields(before)
        self._validate_unique_item_key()
        self._validate_review_status(before)

    def on_update(self):
        sync_applicant_document_review_from_items(self.applicant_document)

    def on_trash(self):
        sync_applicant_document_review_from_items(self.applicant_document)

    def before_delete(self):
        self._validate_delete_allowed()

    def _normalize_fields(self):
        self.applicant_document = (self.applicant_document or "").strip()
        self.item_key = (self.item_key or "").strip()
        self.item_label = (self.item_label or "").strip()
        self.review_notes = (self.review_notes or "").strip()

    def _validate_parent_document(self):
        if not self.applicant_document:
            frappe.throw(_("Applicant Document is required."))
        if not frappe.db.exists("Applicant Document", self.applicant_document):
            frappe.throw(_("Invalid Applicant Document: {0}.").format(self.applicant_document))

    def _validate_permissions(self, before):
        user_roles = set(frappe.get_roles(frappe.session.user))
        if not user_roles & UPLOAD_ROLES:
            frappe.throw(_("You do not have permission to manage Applicant Document Items."))

        if self._review_fields_changed(before) and not user_roles & REVIEW_ROLES:
            frappe.throw(
                _(
                    "Only Admission Officer, Admission Manager, Academic Admin, or System Manager can review document items."
                )
            )

    def _validate_applicant_state(self):
        status = frappe.db.get_value(
            "Applicant Document",
            self.applicant_document,
            "student_applicant",
        )
        if not status:
            return
        application_status = frappe.db.get_value("Student Applicant", status, "application_status")
        if application_status in {"Rejected", "Promoted"}:
            frappe.throw(_("Applicant is read-only in terminal states."))

    def _validate_immutable_fields(self, before):
        if not before:
            return
        for field in ("applicant_document", "item_key"):
            if (before.get(field) or "").strip() != (self.get(field) or "").strip():
                frappe.throw(_("{0} is immutable once set.").format(field.replace("_", " ").title()))

    def _validate_unique_item_key(self):
        if not self.applicant_document or not self.item_key:
            frappe.throw(_("Item Key is required."))

        exists = frappe.db.exists(
            "Applicant Document Item",
            {
                "applicant_document": self.applicant_document,
                "item_key": self.item_key,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(_("Item Key must be unique within an Applicant Document."))

    def _validate_review_status(self, before):
        if not before:
            return
        if before.review_status == self.review_status:
            return
        if self.review_status in {"Approved", "Rejected", "Superseded"}:
            if not self.reviewed_by:
                self.reviewed_by = frappe.session.user
            if not self.reviewed_on:
                self.reviewed_on = now_datetime()

    def _review_fields_changed(self, before):
        if not before:
            status = (self.review_status or "").strip()
            if status and status != "Pending":
                return True
            return bool((self.review_notes or "").strip() or self.reviewed_by or self.reviewed_on)
        return any(
            before.get(field) != self.get(field)
            for field in ("review_status", "review_notes", "reviewed_by", "reviewed_on")
        )

    def _validate_delete_allowed(self):
        if not self.name:
            return
        files_exist = frappe.db.exists(
            "File",
            {
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": self.name,
            },
        )
        if not files_exist:
            return
        user_roles = set(frappe.get_roles(frappe.session.user))
        if "System Manager" in user_roles:
            return
        frappe.throw(_("Cannot delete Applicant Document Item with attached files."))
