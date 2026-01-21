# ifitwala_ed/admission/doctype/student_applicant/student_applicant.py
# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class StudentApplicant(Document):
	def validate(self):
		self._validate_inquiry_link()
		self._validate_application_status()

	def _validate_inquiry_link(self):
		if not self.inquiry:
			return

		previous = self.get_db_value("inquiry")
		if previous and previous != self.inquiry:
			frappe.throw(_("Inquiry link is immutable once set."))

		if not previous and not getattr(self.flags, "from_inquiry_invite", False):
			frappe.throw(_("Inquiry link can only be set via invite_to_apply."))

	def _validate_application_status(self):
		allowed = {
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
		if not self.application_status:
			frappe.throw(_("Application Status is required."))
		if self.application_status not in allowed:
			frappe.throw(_("Invalid Application Status: {0}.").format(self.application_status))

		previous = self.get_db_value("application_status")
		if not previous or previous == self.application_status:
			return

		if previous in {"Rejected", "Promoted"}:
			frappe.throw(_("Application Status cannot change once {0}.").format(previous))
