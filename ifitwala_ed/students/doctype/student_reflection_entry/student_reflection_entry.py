# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_reflection_entry/student_reflection_entry.py

import frappe
from frappe import _
from frappe.model.document import Document


class StudentReflectionEntry(Document):
	def validate(self):
		self._set_context_defaults()
		self._validate_student_anchors()

	def _set_context_defaults(self):
		if self.school and not self.organization:
			self.organization = frappe.db.get_value("School", self.school, "organization")
		if not self.organization:
			frappe.throw(_("Organization is required."))

	def _validate_student_anchors(self):
		if self.program_enrollment:
			owner = frappe.db.get_value("Program Enrollment", self.program_enrollment, "student")
			if owner and owner != self.student:
				frappe.throw(_("Program Enrollment does not belong to the selected student."))

		if self.activity_booking:
			owner = frappe.db.get_value("Activity Booking", self.activity_booking, "student")
			if owner and owner != self.student:
				frappe.throw(_("Activity Booking does not belong to the selected student."))

		if self.task_submission:
			owner = frappe.db.get_value("Task Submission", self.task_submission, "student")
			if owner and owner != self.student:
				frappe.throw(_("Task Submission does not belong to the selected student."))
