# ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.admission.admission_utils import (
    READ_LIKE_PERMISSION_TYPES,
    build_admissions_file_scope_exists_sql,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
)

TARGET_DOCUMENT_ITEM = "Applicant Document Item"
TARGET_HEALTH = "Applicant Health Profile"
TARGET_APPLICATION = "Student Applicant"
MANAGER_ROLES = {"Admission Manager", "Academic Admin", "System Manager"}

DECISIONS_BY_TARGET = {
    TARGET_DOCUMENT_ITEM: {"Approved", "Needs Follow-Up", "Rejected"},
    TARGET_HEALTH: {"Cleared", "Needs Follow-Up"},
    TARGET_APPLICATION: {"Recommend Admit", "Recommend Waitlist", "Recommend Reject", "Needs Follow-Up"},
}


class ApplicantReviewAssignment(Document):
    def validate(self):
        self._normalize_assignment_fields()
        self._sync_scope_from_student_applicant()
        self._validate_assignment_actor()
        self._validate_decision()
        self._validate_target_belongs_to_applicant()
        self._validate_unique_open_assignment()

    def _normalize_assignment_fields(self):
        self.assigned_to_user = (self.assigned_to_user or "").strip() or None
        self.assigned_to_role = (self.assigned_to_role or "").strip() or None
        self.decision = (self.decision or "").strip() or None
        self.source_event = (self.source_event or "").strip() or None

    def _sync_scope_from_student_applicant(self):
        if not self.student_applicant:
            return

        scope_row = frappe.db.get_value(
            "Student Applicant",
            self.student_applicant,
            ["organization", "school", "program_offering"],
            as_dict=True,
        )
        if not scope_row:
            frappe.throw(_("Invalid Student Applicant: {0}.").format(self.student_applicant))

        self.organization = scope_row.get("organization")
        self.school = scope_row.get("school")
        self.program_offering = scope_row.get("program_offering")

    def _validate_assignment_actor(self):
        if bool(self.assigned_to_user) == bool(self.assigned_to_role):
            frappe.throw(_("Exactly one of Assigned To User or Assigned To Role is required."))

    def _validate_decision(self):
        status = (self.status or "").strip()
        target_type = (self.target_type or "").strip()
        decision = (self.decision or "").strip()

        allowed = DECISIONS_BY_TARGET.get(target_type)
        if not allowed:
            frappe.throw(_("Invalid target type: {0}.").format(target_type or _("(empty)")))

        if status == "Open":
            # Keep open rows clean for deterministic reuse/reopen.
            self.decision = None
            return

        if status == "Done" and decision not in allowed:
            frappe.throw(
                _("Decision {0} is not valid for target type {1}.").format(decision or _("(empty)"), target_type)
            )

        if status == "Cancelled":
            return

        if status not in {"Open", "Done", "Cancelled"}:
            frappe.throw(_("Invalid status: {0}.").format(status or _("(empty)")))

    def _validate_target_belongs_to_applicant(self):
        target_type = (self.target_type or "").strip()
        target_name = (self.target_name or "").strip()
        student_applicant = (self.student_applicant or "").strip()

        if not target_type or not target_name or not student_applicant:
            return

        if target_type == TARGET_DOCUMENT_ITEM:
            target_applicant = frappe.db.get_value(
                "Applicant Document Item",
                target_name,
                ["name", "applicant_document"],
                as_dict=True,
            )
            if not target_applicant:
                frappe.throw(_("Invalid Applicant Document Item target: {0}.").format(target_name))
            target_applicant = frappe.db.get_value(
                "Applicant Document",
                target_applicant.get("applicant_document"),
                "student_applicant",
            )
        elif target_type == TARGET_HEALTH:
            target_applicant = frappe.db.get_value("Applicant Health Profile", target_name, "student_applicant")
        elif target_type == TARGET_APPLICATION:
            target_applicant = target_name
        else:
            frappe.throw(_("Unsupported target type: {0}.").format(target_type))

        if target_applicant != student_applicant:
            frappe.throw(_("Target does not belong to Student Applicant {0}.").format(student_applicant))

    def _validate_unique_open_assignment(self):
        if (self.status or "").strip() != "Open":
            return

        filters = {
            "target_type": self.target_type,
            "target_name": self.target_name,
            "status": "Open",
            "name": ["!=", self.name],
        }
        if self.assigned_to_user:
            filters["assigned_to_user"] = self.assigned_to_user
        else:
            filters["assigned_to_role"] = self.assigned_to_role

        if frappe.db.exists("Applicant Review Assignment", filters):
            frappe.throw(_("An open assignment already exists for this target and reviewer."))


def get_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        return "1=0"
    if not is_admissions_file_staff_user(resolved_user):
        return "1=0"

    scope_condition = build_admissions_file_scope_exists_sql(
        user=resolved_user,
        student_applicant_expr_sql="`tabApplicant Review Assignment`.`student_applicant`",
    )
    if scope_condition == "1=0":
        return "1=0"

    roles = set(frappe.get_roles(resolved_user))
    if resolved_user == "Administrator" or roles & MANAGER_ROLES:
        return scope_condition or None

    escaped_user = frappe.db.escape(resolved_user)
    role_values = ", ".join(
        frappe.db.escape(role_name)
        for role_name in sorted((role_name or "").strip() for role_name in roles if (role_name or "").strip())
    )
    actor_parts = [f"`tabApplicant Review Assignment`.`assigned_to_user` = {escaped_user}"]
    if role_values:
        actor_parts.append(f"`tabApplicant Review Assignment`.`assigned_to_role` IN ({role_values})")
    actor_condition = "(" + " OR ".join(actor_parts) + ")"

    if scope_condition is None:
        return actor_condition
    return f"({scope_condition}) AND {actor_condition}"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False
    if not is_admissions_file_staff_user(resolved_user):
        return False

    roles = set(frappe.get_roles(resolved_user))
    manager_access = resolved_user == "Administrator" or bool(roles & MANAGER_ROLES)

    if op in READ_LIKE_PERMISSION_TYPES:
        if not doc:
            return True
        student_applicant = _resolve_assignment_student_applicant(doc)
        if not has_scoped_staff_access_to_student_applicant(user=resolved_user, student_applicant=student_applicant):
            return False
        if manager_access:
            return True
        return _reviewer_matches_assignment(doc, user=resolved_user, roles=roles)

    if op in {"write", "create", "delete", "submit", "cancel", "amend"}:
        if not manager_access:
            return False
        if op == "create" and not doc:
            return True
        if not doc:
            return True
        student_applicant = _resolve_assignment_student_applicant(doc)
        return has_scoped_staff_access_to_student_applicant(user=resolved_user, student_applicant=student_applicant)

    return False


def _resolve_assignment_student_applicant(doc) -> str:
    if isinstance(doc, str):
        assignment_name = (doc or "").strip()
        if not assignment_name:
            return ""
        return (frappe.db.get_value("Applicant Review Assignment", assignment_name, "student_applicant") or "").strip()

    if isinstance(doc, dict):
        student_applicant = (doc.get("student_applicant") or "").strip()
        if student_applicant:
            return student_applicant
        assignment_name = (doc.get("name") or "").strip()
    else:
        student_applicant = (getattr(doc, "student_applicant", None) or "").strip()
        if student_applicant:
            return student_applicant
        assignment_name = (getattr(doc, "name", None) or "").strip()

    if not assignment_name:
        return ""
    return (frappe.db.get_value("Applicant Review Assignment", assignment_name, "student_applicant") or "").strip()


def _reviewer_matches_assignment(doc, *, user: str, roles: set[str]) -> bool:
    if isinstance(doc, dict):
        assigned_to_user = (doc.get("assigned_to_user") or "").strip()
        assigned_to_role = (doc.get("assigned_to_role") or "").strip()
    else:
        assigned_to_user = (getattr(doc, "assigned_to_user", None) or "").strip()
        assigned_to_role = (getattr(doc, "assigned_to_role", None) or "").strip()

    if assigned_to_user:
        return assigned_to_user == user
    if assigned_to_role:
        return assigned_to_role in roles
    return False
