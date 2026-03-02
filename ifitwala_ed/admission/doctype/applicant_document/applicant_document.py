# ifitwala_ed/admission/doctype/applicant_document/applicant_document.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES

UPLOAD_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", "Admissions Applicant"}
REVIEW_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager"}


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

    def on_update(self):
        before = self.get_doc_before_save()
        if not before:
            return
        self._append_update_timeline(before)

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
            frappe.throw(
                _("Only Admission Officer, Admission Manager, Academic Admin, or System Manager can review documents.")
            )

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
            frappe.throw(
                _("Only Admission Officer, Admission Manager, Academic Admin, or System Manager can set Is Promotable.")
            )

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

    def _append_update_timeline(self, before):
        changes = []
        previous_status = (before.get("review_status") or "Pending").strip()
        current_status = (self.get("review_status") or "Pending").strip()
        if previous_status != current_status:
            changes.append(_("Review Status: {0} -> {1}").format(previous_status, current_status))

        before_notes = (before.get("review_notes") or "").strip()
        current_notes = (self.get("review_notes") or "").strip()
        if before_notes != current_notes:
            changes.append(_("Review notes updated") if current_notes else _("Review notes cleared"))

        if cint(before.get("is_promotable")) != cint(self.get("is_promotable")):
            changes.append(
                _("Is Promotable: {0} -> {1}").format(
                    _("Yes") if cint(before.get("is_promotable")) else _("No"),
                    _("Yes") if cint(self.get("is_promotable")) else _("No"),
                )
            )

        before_target = (before.get("promotion_target") or "").strip()
        current_target = (self.get("promotion_target") or "").strip()
        if before_target != current_target:
            changes.append(
                _("Promotion Target: {0} -> {1}").format(
                    before_target or _("None"),
                    current_target or _("None"),
                )
            )

        if not changes:
            return

        document_label = (
            frappe.db.get_value("Applicant Document Type", self.document_type, "code") or self.document_type
        )
        message = _("Applicant document updated: {0} ({1}) by {2} on {3}. Changes: {4}.").format(
            frappe.bold(document_label),
            frappe.bold(self.name),
            frappe.bold(frappe.session.user),
            now_datetime(),
            "; ".join(changes),
        )

        try:
            applicant = frappe.get_doc("Student Applicant", self.student_applicant)
            applicant.add_comment("Comment", text=message)
        except Exception:
            frappe.log_error(
                message=frappe.as_json(
                    {
                        "student_applicant": self.student_applicant,
                        "applicant_document": self.name,
                        "changes": changes,
                    }
                ),
                title="Applicant document update timeline write failed",
            )


def _latest_review_actor(rows: list[dict], target_status: str) -> tuple[str | None, str | None]:
    matching = [row for row in rows if (row.get("review_status") or "").strip() == target_status]
    if not matching:
        return None, None
    matching.sort(key=lambda row: row.get("reviewed_on") or "", reverse=True)
    picked = matching[0]
    return (picked.get("reviewed_by") or None, picked.get("reviewed_on") or None)


def sync_applicant_document_review_from_items(applicant_document: str | None) -> dict:
    parent_name = (applicant_document or "").strip()
    if not parent_name:
        return {}
    if not frappe.db.exists("Applicant Document", parent_name):
        return {}

    item_rows = frappe.get_all(
        "Applicant Document Item",
        filters={"applicant_document": parent_name},
        fields=["review_status", "reviewed_by", "reviewed_on"],
    )
    statuses = [(row.get("review_status") or "Pending").strip() for row in item_rows]

    if not statuses:
        target_status = "Pending"
        reviewed_by = None
        reviewed_on = None
    elif any(status == "Rejected" for status in statuses):
        target_status = "Rejected"
        reviewed_by, reviewed_on = _latest_review_actor(item_rows, "Rejected")
    elif all(status == "Approved" for status in statuses):
        target_status = "Approved"
        reviewed_by, reviewed_on = _latest_review_actor(item_rows, "Approved")
    else:
        target_status = "Pending"
        reviewed_by = None
        reviewed_on = None

    current = (
        frappe.db.get_value(
            "Applicant Document",
            parent_name,
            ["review_status", "reviewed_by", "reviewed_on"],
            as_dict=True,
        )
        or {}
    )
    updates = {}
    if (current.get("review_status") or "Pending") != target_status:
        updates["review_status"] = target_status
    if (current.get("reviewed_by") or None) != reviewed_by:
        updates["reviewed_by"] = reviewed_by
    if (current.get("reviewed_on") or None) != reviewed_on:
        updates["reviewed_on"] = reviewed_on

    if updates:
        frappe.db.set_value(
            "Applicant Document",
            parent_name,
            updates,
            update_modified=False,
        )

    return {
        "review_status": target_status,
        "reviewed_by": reviewed_by,
        "reviewed_on": reviewed_on,
    }
