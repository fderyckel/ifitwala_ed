# ifitwala_ed/admission/doctype/student_applicant/student_applicant.py
# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class StudentApplicant(Document):
	def validate(self):
		self._validate_inquiry_link()

	def _validate_inquiry_link(self):
		if not self.inquiry:
			return

		previous = self.get_db_value("inquiry")
		if previous and previous != self.inquiry:
			frappe.throw(_("Inquiry link is immutable once set."))
