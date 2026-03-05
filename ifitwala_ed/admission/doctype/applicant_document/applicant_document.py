# ifitwala_ed/admission/doctype/applicant_document/applicant_document.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    READ_LIKE_PERMISSION_TYPES,
    build_admissions_file_scope_exists_sql,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
    normalize_email_value,
)

ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
UPLOAD_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", ADMISSIONS_APPLICANT_ROLE}
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

        if is_admissions_file_staff_user(frappe.session.user):
            if not has_scoped_staff_access_to_student_applicant(
                user=frappe.session.user,
                student_applicant=self.student_applicant,
            ):
                frappe.throw(_("You do not have permission to manage this Applicant Document."), frappe.PermissionError)

        is_staff_reviewer = bool(user_roles & REVIEW_ROLES)
        is_applicant = ADMISSIONS_APPLICANT_ROLE in user_roles
        if is_applicant and not is_staff_reviewer:
            if not _is_student_applicant_self_user(self.student_applicant, frappe.session.user):
                frappe.throw(_("You do not have permission to manage this Applicant Document."), frappe.PermissionError)

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


def get_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    conditions: list[str] = []
    if is_admissions_file_staff_user(resolved_user):
        staff_condition = build_admissions_file_scope_exists_sql(
            user=resolved_user,
            student_applicant_expr_sql="`tabApplicant Document`.`student_applicant`",
        )
        if staff_condition is None:
            return None
        if staff_condition != "1=0":
            conditions.append(f"({staff_condition})")

    roles = set(frappe.get_roles(resolved_user))
    if ADMISSIONS_APPLICANT_ROLE in roles:
        escaped_user = frappe.db.escape(resolved_user)
        conditions.append(
            "("
            "EXISTS ("
            "SELECT 1 FROM `tabStudent Applicant` sa "
            "WHERE sa.name = `tabApplicant Document`.`student_applicant` "
            f"AND (sa.applicant_user = {escaped_user} "
            f"OR sa.portal_account_email = {escaped_user} "
            f"OR sa.applicant_email = {escaped_user})"
            ")"
            ")"
        )

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
        if op == "create":
            if not doc:
                return True
        if not doc:
            return True
        student_applicant = _resolve_document_student_applicant(doc)
        return has_scoped_staff_access_to_student_applicant(user=resolved_user, student_applicant=student_applicant)

    roles = set(frappe.get_roles(resolved_user))
    if ADMISSIONS_APPLICANT_ROLE not in roles:
        return False

    applicant_ops = READ_LIKE_PERMISSION_TYPES | {"write", "create"}
    if op not in applicant_ops:
        return False
    if op == "create":
        if not doc:
            return True
    if not doc:
        return op in READ_LIKE_PERMISSION_TYPES
    return _is_document_applicant_self_user(doc=doc, user=resolved_user)


def _resolve_document_student_applicant(doc) -> str:
    if isinstance(doc, str):
        document_name = (doc or "").strip()
        if not document_name:
            return ""
        return (frappe.db.get_value("Applicant Document", document_name, "student_applicant") or "").strip()

    if isinstance(doc, dict):
        student_applicant = (doc.get("student_applicant") or "").strip()
        if student_applicant:
            return student_applicant
        document_name = (doc.get("name") or "").strip()
    else:
        student_applicant = (getattr(doc, "student_applicant", None) or "").strip()
        if student_applicant:
            return student_applicant
        document_name = (getattr(doc, "name", None) or "").strip()

    if not document_name:
        return ""
    return (frappe.db.get_value("Applicant Document", document_name, "student_applicant") or "").strip()


def _is_student_applicant_self_user(student_applicant: str | None, user: str | None) -> bool:
    applicant_name = (student_applicant or "").strip()
    resolved_user = (user or "").strip()
    if not applicant_name or not resolved_user:
        return False

    applicant_row = frappe.db.get_value(
        "Student Applicant",
        applicant_name,
        ["applicant_user", "portal_account_email", "applicant_email"],
        as_dict=True,
    )
    if not applicant_row:
        return False

    if (applicant_row.get("applicant_user") or "").strip() == resolved_user:
        return True

    normalized_user = normalize_email_value(resolved_user)
    return normalized_user in {
        normalize_email_value(applicant_row.get("portal_account_email")),
        normalize_email_value(applicant_row.get("applicant_email")),
    }


def _is_document_applicant_self_user(*, doc, user: str) -> bool:
    student_applicant = _resolve_document_student_applicant(doc)
    return _is_student_applicant_self_user(student_applicant, user)
