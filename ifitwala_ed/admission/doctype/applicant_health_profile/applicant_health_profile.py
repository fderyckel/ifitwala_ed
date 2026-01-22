# ifitwala_ed/admission/doctype/applicant_health_profile/applicant_health_profile.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES


FAMILY_ROLES = {"Guardian"}
ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
STAFF_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager"}


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

		status = self._get_applicant_status()
		if status in {"Rejected", "Promoted"}:
			frappe.throw(_("Applicant is read-only in terminal states."))

		if is_family:
			if status not in {"Invited", "In Progress", "Missing Info"}:
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
			return bool(self.review_status or self.review_notes or self.reviewed_by or self.reviewed_on)
		return any(
			before.get(field) != self.get(field)
			for field in ("review_status", "review_notes", "reviewed_by", "reviewed_on")
		)

	def _get_applicant_status(self):
		if not self.student_applicant:
			return None
		return frappe.db.get_value(
			"Student Applicant", self.student_applicant, "application_status"
		)
