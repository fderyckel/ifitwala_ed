# ifitwala_ed/admission/doctype/applicant_health_profile/applicant_health_profile.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    READ_LIKE_PERMISSION_TYPES,
    build_admissions_file_scope_exists_sql,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
    normalize_email_value,
)

FAMILY_ROLES = {"Guardian"}
ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
STAFF_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", "Nurse"}


class ApplicantHealthProfile(Document):
    def validate(self):
        before = self.get_doc_before_save() if not self.is_new() else None
        self._validate_permissions(before)
        self._validate_student_applicant_immutable(before)
        self._apply_review_metadata(before)

    def _validate_permissions(self, before):
        user_roles = set(frappe.get_roles(frappe.session.user))
        is_family = bool(user_roles & (FAMILY_ROLES | {ADMISSIONS_APPLICANT_ROLE}))
        is_staff = bool(user_roles & STAFF_ROLES)

        if not is_family and not is_staff:
            frappe.throw(_("You do not have permission to edit Applicant Health Profiles."))

        if is_staff and is_admissions_file_staff_user(frappe.session.user):
            if not has_scoped_staff_access_to_student_applicant(
                user=frappe.session.user,
                student_applicant=self.student_applicant,
            ):
                frappe.throw(
                    _("You do not have permission to edit this Applicant Health Profile."),
                    frappe.PermissionError,
                )

        if is_family:
            if not _is_family_linked_to_student_applicant(self.student_applicant, frappe.session.user, user_roles):
                frappe.throw(
                    _("You do not have permission to edit this Applicant Health Profile."), frappe.PermissionError
                )

        status = self._get_applicant_status()
        if status in {"Rejected", "Promoted"}:
            frappe.throw(_("Applicant is read-only in terminal states."))

        if is_family:
            if status not in {
                "Draft",
                "Invited",
                "In Progress",
                "Submitted",
                "Under Review",
                "Missing Info",
                "Approved",
                "Withdrawn",
            }:
                frappe.throw(_("Family edits are not allowed for this Applicant status."))

        if self._review_fields_changed(before) and not is_staff:
            frappe.throw(_("Only staff can update health review fields."))

    def _validate_student_applicant_immutable(self, before):
        if self.is_new():
            return
        if not before:
            return
        if before.student_applicant != self.student_applicant:
            frappe.throw(_("Student Applicant is immutable once set."))

    def _apply_review_metadata(self, before):
        if not self.review_status:
            return
        if before and before.review_status == self.review_status:
            return
        if self.review_status in {"Needs Follow-Up", "Cleared"}:
            if not self.reviewed_by:
                self.reviewed_by = frappe.session.user
            if not self.reviewed_on:
                self.reviewed_on = now_datetime()

    def _review_fields_changed(self, before):
        if not before:
            return bool(
                self.review_notes
                or self.reviewed_by
                or self.reviewed_on
                or (self.review_status and self.review_status != "Pending")
            )
        return any(
            before.get(field) != self.get(field)
            for field in ("review_status", "review_notes", "reviewed_by", "reviewed_on")
        )

    def _get_applicant_status(self):
        if not self.student_applicant:
            return None
        return frappe.db.get_value("Student Applicant", self.student_applicant, "application_status")


def get_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    roles = set(frappe.get_roles(resolved_user))
    if "Nurse" in roles:
        return None

    conditions: list[str] = []
    if is_admissions_file_staff_user(resolved_user):
        staff_condition = build_admissions_file_scope_exists_sql(
            user=resolved_user,
            student_applicant_expr_sql="`tabApplicant Health Profile`.`student_applicant`",
        )
        if staff_condition is None:
            return None
        if staff_condition != "1=0":
            conditions.append(f"({staff_condition})")

    escaped_user = frappe.db.escape(resolved_user)
    if ADMISSIONS_APPLICANT_ROLE in roles:
        conditions.append(
            "("
            "EXISTS ("
            "SELECT 1 FROM `tabStudent Applicant` sa "
            "WHERE sa.name = `tabApplicant Health Profile`.`student_applicant` "
            f"AND (sa.applicant_user = {escaped_user} "
            f"OR sa.portal_account_email = {escaped_user} "
            f"OR sa.applicant_email = {escaped_user})"
            ")"
            ")"
        )

    if FAMILY_ROLES & roles:
        conditions.append(
            "("
            "EXISTS ("
            "SELECT 1 FROM `tabStudent Applicant Guardian` sag "
            "WHERE sag.parent = `tabApplicant Health Profile`.`student_applicant` "
            "AND sag.parenttype = 'Student Applicant' "
            "AND sag.parentfield = 'guardians' "
            f"AND sag.user = {escaped_user}"
            ")"
            ")"
        )

    return " OR ".join(conditions) if conditions else "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False

    roles = set(frappe.get_roles(resolved_user))
    if "Nurse" in roles:
        return True

    if is_admissions_file_staff_user(resolved_user):
        staff_ops = READ_LIKE_PERMISSION_TYPES | {"write", "create", "delete", "submit", "cancel", "amend"}
        if op not in staff_ops:
            return False
        if op == "create":
            if not doc:
                return True
        if not doc:
            return True
        student_applicant = _resolve_health_student_applicant(doc)
        return has_scoped_staff_access_to_student_applicant(user=resolved_user, student_applicant=student_applicant)

    family_roles = FAMILY_ROLES | {ADMISSIONS_APPLICANT_ROLE}
    if not (roles & family_roles):
        return False

    family_ops = READ_LIKE_PERMISSION_TYPES | {"write", "create"}
    if op not in family_ops:
        return False
    if op == "create":
        if not doc:
            return True
    if not doc:
        return op in READ_LIKE_PERMISSION_TYPES

    student_applicant = _resolve_health_student_applicant(doc)
    return _is_family_linked_to_student_applicant(student_applicant, resolved_user, roles)


def _resolve_health_student_applicant(doc) -> str:
    if isinstance(doc, str):
        health_name = (doc or "").strip()
        if not health_name:
            return ""
        return (frappe.db.get_value("Applicant Health Profile", health_name, "student_applicant") or "").strip()

    if isinstance(doc, dict):
        student_applicant = (doc.get("student_applicant") or "").strip()
        if student_applicant:
            return student_applicant
        health_name = (doc.get("name") or "").strip()
    else:
        student_applicant = (getattr(doc, "student_applicant", None) or "").strip()
        if student_applicant:
            return student_applicant
        health_name = (getattr(doc, "name", None) or "").strip()

    if not health_name:
        return ""
    return (frappe.db.get_value("Applicant Health Profile", health_name, "student_applicant") or "").strip()


def _is_family_linked_to_student_applicant(student_applicant: str | None, user: str, roles: set[str]) -> bool:
    applicant_name = (student_applicant or "").strip()
    if not applicant_name:
        return False

    if ADMISSIONS_APPLICANT_ROLE in roles and _is_applicant_self_user(applicant_name, user):
        return True
    if FAMILY_ROLES & roles and _is_guardian_linked_user(applicant_name, user):
        return True
    return False


def _is_applicant_self_user(student_applicant: str, user: str) -> bool:
    applicant_row = frappe.db.get_value(
        "Student Applicant",
        student_applicant,
        ["applicant_user", "portal_account_email", "applicant_email"],
        as_dict=True,
    )
    if not applicant_row:
        return False

    if (applicant_row.get("applicant_user") or "").strip() == user:
        return True

    normalized_user = normalize_email_value(user)
    return normalized_user in {
        normalize_email_value(applicant_row.get("portal_account_email")),
        normalize_email_value(applicant_row.get("applicant_email")),
    }


def _is_guardian_linked_user(student_applicant: str, user: str) -> bool:
    return bool(
        frappe.db.exists(
            "Student Applicant Guardian",
            {
                "parent": student_applicant,
                "parenttype": "Student Applicant",
                "parentfield": "guardians",
                "user": user,
            },
        )
    )
