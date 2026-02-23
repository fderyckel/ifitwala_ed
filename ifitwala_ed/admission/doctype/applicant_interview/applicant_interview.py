# ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, now_datetime

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES

STAFF_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager"}


class ApplicantInterview(Document):
    def validate(self):
        self._validate_permissions()
        self._validate_applicant_state()

    def after_insert(self):
        self._add_audit_comment("Interview recorded")

    def on_update(self):
        # Frappe calls on_update during insert as well; avoid duplicate insert-time audit rows.
        if getattr(self.flags, "in_insert", False):
            return
        if not self.get_doc_before_save():
            return
        self._add_audit_comment("Interview updated")

    def _validate_permissions(self):
        user_roles = set(frappe.get_roles(frappe.session.user))
        if not user_roles & STAFF_ROLES:
            frappe.throw(_("You do not have permission to manage Applicant Interviews."))

    def _validate_applicant_state(self):
        if not self.student_applicant:
            return
        status = frappe.db.get_value("Student Applicant", self.student_applicant, "application_status")
        if status in {"Rejected", "Promoted"}:
            frappe.throw(_("Applicant is read-only in terminal states."))

    def _add_audit_comment(self, label):
        if not self.student_applicant:
            return
        applicant = frappe.get_doc("Student Applicant", self.student_applicant)
        interview_link = get_link_to_form("Applicant Interview", self.name)
        applicant.add_comment(
            "Comment",
            text=_("{0}: {1} by {2} on {3}.").format(
                label,
                interview_link,
                frappe.bold(frappe.session.user),
                now_datetime(),
            ),
        )
