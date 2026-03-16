# ifitwala_ed/admission/doctype/applicant_document_item/applicant_document_item.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
    build_admissions_portal_access_exists_sql,
    user_can_access_student_applicant,
)
from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    READ_LIKE_PERMISSION_TYPES,
    build_admissions_file_scope_exists_sql,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
)
from ifitwala_ed.admission.doctype.applicant_document.applicant_document import (
    sync_applicant_document_review_from_items,
)

UPLOAD_ROLES = ADMISSIONS_ROLES | {
    "Academic Admin",
    "System Manager",
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
}
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
        self._validate_delete_allowed()
        sync_applicant_document_review_from_items(self.applicant_document)

    def before_trash(self):
        self._validate_delete_allowed()

    # Keep compatibility with older hook naming used in this app.
    def before_delete(self):
        self.before_trash()

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

        student_applicant = _resolve_item_student_applicant(self)
        if is_admissions_file_staff_user(frappe.session.user):
            if not has_scoped_staff_access_to_student_applicant(
                user=frappe.session.user,
                student_applicant=student_applicant,
            ):
                frappe.throw(
                    _("You do not have permission to manage this Applicant Document Item."), frappe.PermissionError
                )
        elif user_roles & {ADMISSIONS_APPLICANT_ROLE, ADMISSIONS_FAMILY_ROLE}:
            if not user_can_access_student_applicant(user=frappe.session.user, student_applicant=student_applicant):
                frappe.throw(
                    _("You do not have permission to manage this Applicant Document Item."), frappe.PermissionError
                )

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


def get_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    conditions: list[str] = []
    if is_admissions_file_staff_user(resolved_user):
        staff_condition = build_admissions_file_scope_exists_sql(
            user=resolved_user,
            student_applicant_expr_sql=(
                "(SELECT ad.student_applicant "
                "FROM `tabApplicant Document` ad "
                "WHERE ad.name = `tabApplicant Document Item`.`applicant_document`)"
            ),
        )
        if staff_condition is None:
            return None
        if staff_condition != "1=0":
            conditions.append(f"({staff_condition})")

    portal_condition = build_admissions_portal_access_exists_sql(
        user=resolved_user,
        student_applicant_expr_sql=(
            "(SELECT ad.student_applicant "
            "FROM `tabApplicant Document` ad "
            "WHERE ad.name = `tabApplicant Document Item`.`applicant_document`)"
        ),
    )
    if portal_condition != "1=0":
        conditions.append(f"({portal_condition})")

    return " OR ".join(conditions) if conditions else "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False

    if is_admissions_file_staff_user(resolved_user):
        staff_ops = READ_LIKE_PERMISSION_TYPES | {"write", "create", "delete", "submit", "cancel", "amend"}
        if op not in staff_ops:
            return False
        if op == "create" and not doc:
            return True
        if not doc:
            return True
        student_applicant = _resolve_item_student_applicant(doc)
        return has_scoped_staff_access_to_student_applicant(user=resolved_user, student_applicant=student_applicant)

    roles = set(frappe.get_roles(resolved_user))
    if not roles & {ADMISSIONS_APPLICANT_ROLE, ADMISSIONS_FAMILY_ROLE}:
        return False

    applicant_ops = READ_LIKE_PERMISSION_TYPES | {"write", "create"}
    if op not in applicant_ops:
        return False
    if op == "create" and not doc:
        return True
    if not doc:
        return op in READ_LIKE_PERMISSION_TYPES
    return user_can_access_student_applicant(
        user=resolved_user,
        student_applicant=_resolve_item_student_applicant(doc),
    )


def _resolve_item_student_applicant(doc) -> str:
    if isinstance(doc, str):
        item_name = (doc or "").strip()
        if not item_name:
            return ""
        parent_name = (frappe.db.get_value("Applicant Document Item", item_name, "applicant_document") or "").strip()
        if not parent_name:
            return ""
        return (frappe.db.get_value("Applicant Document", parent_name, "student_applicant") or "").strip()

    if isinstance(doc, dict):
        parent_name = (doc.get("applicant_document") or "").strip()
        item_name = (doc.get("name") or "").strip()
    else:
        parent_name = (getattr(doc, "applicant_document", None) or "").strip()
        item_name = (getattr(doc, "name", None) or "").strip()

    if not parent_name and item_name:
        parent_name = (frappe.db.get_value("Applicant Document Item", item_name, "applicant_document") or "").strip()
    if not parent_name:
        return ""
    return (frappe.db.get_value("Applicant Document", parent_name, "student_applicant") or "").strip()
