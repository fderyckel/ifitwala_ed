# ifitwala_ed/admission/doctype/applicant_document/applicant_document.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES

UPLOAD_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", "Admissions Applicant"}
REVIEW_ROLES = {"Academic Admin", "System Manager"}


class ApplicantDocument(Document):
    def validate(self):
        before = self.get_doc_before_save() if not self.is_new() else None
        self._validate_permissions(before)
        self._validate_applicant_state()
        self._validate_immutable_fields(before)
        self._validate_unique_document_type()
        self._validate_review_status(before)
        self._validate_promotion_flags(before)

    def before_delete(self):
        self._validate_delete_allowed()

    def get_file_routing_context(self, file_doc):
        doc_type_code = frappe.db.get_value("Applicant Document Type", self.document_type, "code") or self.document_type
        return {
            "root_folder": "Home/Admissions",
            "subfolder": f"Applicant/{self.student_applicant}/Documents/{doc_type_code}",
            "file_category": "Admissions Applicant Document",
            "logical_key": doc_type_code,
        }

    def _validate_permissions(self, before):
        user_roles = set(frappe.get_roles(frappe.session.user))
        if not user_roles & UPLOAD_ROLES:
            frappe.throw(_("You do not have permission to manage Applicant Documents."))

        if self._review_fields_changed(before) and not user_roles & REVIEW_ROLES:
            frappe.throw(_("Only Academic Admin or System Manager can review documents."))

    def _validate_applicant_state(self):
        status = frappe.db.get_value("Student Applicant", self.student_applicant, "application_status")
        if status in {"Rejected", "Promoted"}:
            frappe.throw(_("Applicant is read-only in terminal states."))

    def _validate_immutable_fields(self, before):
        if not before:
            return
        for field in ("student_applicant", "document_type"):
            if before.get(field) != self.get(field):
                frappe.throw(_("{0} is immutable once set.").format(field.replace("_", " ").title()))

    def _validate_unique_document_type(self):
        if not self.student_applicant or not self.document_type:
            return
        exists = frappe.db.exists(
            "Applicant Document",
            {
                "student_applicant": self.student_applicant,
                "document_type": self.document_type,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(_("Only one Applicant Document per document type is allowed per Applicant."))

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

    def _validate_promotion_flags(self, before):
        if not self.is_promotable:
            return
        if self.review_status != "Approved":
            frappe.throw(_("Is Promotable requires Review Status = Approved."))
        user_roles = set(frappe.get_roles(frappe.session.user))
        if not user_roles & REVIEW_ROLES:
            frappe.throw(_("Only Academic Admin or System Manager can set Is Promotable."))

    def _review_fields_changed(self, before):
        if not before:
            status = (self.review_status or "").strip()
            # New rows are born with default Pending; that is not a review action.
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
                "attached_to_doctype": "Applicant Document",
                "attached_to_name": self.name,
            },
        )
        if not files_exist:
            return
        user_roles = set(frappe.get_roles(frappe.session.user))
        if "System Manager" in user_roles:
            return
        frappe.throw(_("Cannot delete Applicant Document with attached files."))
