# ifitwala_ed/admission/doctype/student_applicant/student_applicant.py
# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from ifitwala_ed.admission.admission_utils import ensure_admissions_permission, ADMISSIONS_ROLES


FAMILY_ROLES = {"Guardian"}

STATUS_SET = {
	"Draft",
	"Invited",
	"In Progress",
	"Submitted",
	"Under Review",
	"Missing Info",
	"Approved",
	"Rejected",
	"Promoted",
}

STATUS_TRANSITIONS = {
	"Draft": {"Invited"},
	"Invited": {"In Progress"},
	"In Progress": {"Submitted"},
	"Submitted": {"Under Review"},
	"Under Review": {"Missing Info", "Approved", "Rejected"},
	"Missing Info": {"In Progress"},
	"Approved": {"Promoted"},
}

EDIT_RULES = {
	"Draft": {"family": False, "staff": True},
	"Invited": {"family": True, "staff": True},
	"In Progress": {"family": True, "staff": True},
	"Submitted": {"family": False, "staff": True},
	"Under Review": {"family": False, "staff": True},
	"Missing Info": {"family": True, "staff": True},
	"Approved": {"family": False, "staff": True},
	"Rejected": {"family": False, "staff": False},
	"Promoted": {"family": False, "staff": False},
}


class StudentApplicant(Document):
	def validate(self):
		before = self.get_doc_before_save() if not self.is_new() else None
		self._validate_inquiry_link(before)
		self._validate_student_link(before)
		self._validate_application_status(before)
		self._validate_edit_permissions(before)

	def _validate_inquiry_link(self, before):
		if not self.inquiry:
			return

		previous = before.inquiry if before else self.get_db_value("inquiry")
		if previous and previous != self.inquiry:
			frappe.throw(_("Inquiry link is immutable once set."))

		if not previous and not getattr(self.flags, "from_inquiry_invite", False):
			frappe.throw(_("Inquiry link can only be set via invite_to_apply."))

	def _validate_student_link(self, before):
		if not self.student:
			return

		previous = before.student if before else self.get_db_value("student")
		if previous and previous != self.student:
			frappe.throw(_("Student link is immutable once set."))

		if not previous:
			frappe.throw(_("Student link can only be set during promotion."))

	def _validate_application_status(self, before):
		if not self.application_status:
			frappe.throw(_("Application Status is required."))
		if self.application_status not in STATUS_SET:
			frappe.throw(_("Invalid Application Status: {0}.").format(self.application_status))

		if self.is_new():
			if self.application_status == "Invited" and getattr(self.flags, "from_inquiry_invite", False):
				return
			if self.application_status != "Draft":
				frappe.throw(_("New Student Applicants must start in Draft."))
			return

		previous = before.application_status if before else self.get_db_value("application_status")
		if not previous or previous == self.application_status:
			return

		if not getattr(self.flags, "allow_status_change", False):
			frappe.throw(_("Application Status must be changed via lifecycle methods."))

		self._validate_status_transition(previous, self.application_status)

	def _validate_status_transition(self, from_status, to_status):
		allowed = STATUS_TRANSITIONS.get(from_status, set())
		if to_status not in allowed:
			frappe.throw(
				_("Invalid Application Status transition from {0} to {1}.").format(from_status, to_status)
			)

	def _validate_edit_permissions(self, before):
		user = frappe.session.user
		roles = set(frappe.get_roles(user))
		is_admissions = bool(roles & ADMISSIONS_ROLES)
		is_family = bool(roles & FAMILY_ROLES)

		if self.is_new():
			if not is_admissions:
				frappe.throw(_("Only Admissions staff can create Student Applicants."))
			return

		if not before:
			return

		status_for_edit = self.application_status
		if (
			before.application_status != self.application_status
			and getattr(self.flags, "allow_status_change", False)
		):
			status_for_edit = before.application_status

		rules = EDIT_RULES.get(status_for_edit)
		if not rules:
			frappe.throw(_("Invalid Application Status: {0}.").format(status_for_edit))

		if not is_admissions and not is_family:
			if self._has_changes(before):
				frappe.throw(_("You do not have permission to edit this Applicant."))
			return

		if is_family:
			if not rules["family"] and self._has_changes(before):
				frappe.throw(
					_("Family edits are not allowed when status is {0}.").format(status_for_edit)
				)
			return

		if is_admissions and not rules["staff"]:
			if self._has_changes(before):
				if getattr(self.flags, "allow_status_change", False) and self._only_status_changed(before):
					return
				frappe.throw(_("Edits are not allowed when status is {0}.").format(status_for_edit))

	def _has_changes(self, before, ignore_fields=None):
		if not before:
			return False

		ignore = set(ignore_fields or [])
		ignore.update({"modified", "modified_by", "creation", "owner", "idx", "docstatus"})
		for df in self.meta.fields:
			fieldname = df.fieldname
			if not fieldname or fieldname in ignore:
				continue
			if self.get(fieldname) != before.get(fieldname):
				return True
		return False

	def _only_status_changed(self, before):
		return not self._has_changes(before, ignore_fields={"application_status"})

	def _set_status(self, new_status, action_label):
		ensure_admissions_permission()
		if self.is_new():
			frappe.throw(_("Save the Student Applicant before changing status."))

		if self.application_status == new_status:
			return {"ok": True, "changed": False, "status": new_status}

		self._validate_status_transition(self.application_status, new_status)
		previous = self.application_status
		self.flags.allow_status_change = True
		self.application_status = new_status
		self.save(ignore_permissions=True)

		self.add_comment(
			"Comment",
			text=_(
				"{0} by {1} on {2}. Status: {3} -> {4}."
			).format(action_label, frappe.bold(frappe.session.user), now_datetime(), previous, new_status),
		)
		return {"ok": True, "changed": True, "status": new_status}

	@frappe.whitelist()
	def mark_in_progress(self):
		return self._set_status("In Progress", "Marked In Progress")

	@frappe.whitelist()
	def submit_application(self):
		return self._set_status("Submitted", "Application submitted")

	@frappe.whitelist()
	def mark_missing_info(self):
		return self._set_status("Missing Info", "Marked Missing Info")

	@frappe.whitelist()
	def approve_application(self):
		return self._set_status("Approved", "Application approved")

	@frappe.whitelist()
	def reject_application(self):
		return self._set_status("Rejected", "Application rejected")
