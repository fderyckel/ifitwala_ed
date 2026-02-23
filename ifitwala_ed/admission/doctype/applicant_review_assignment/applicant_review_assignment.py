# ifitwala_ed/admission/doctype/applicant_review_assignment/applicant_review_assignment.py

import frappe
from frappe import _
from frappe.model.document import Document

TARGET_DOCUMENT = "Applicant Document"
TARGET_HEALTH = "Applicant Health Profile"
TARGET_APPLICATION = "Student Applicant"

DECISIONS_BY_TARGET = {
    TARGET_DOCUMENT: {"Approved", "Needs Follow-Up", "Rejected"},
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

        if target_type == TARGET_DOCUMENT:
            target_applicant = frappe.db.get_value("Applicant Document", target_name, "student_applicant")
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
