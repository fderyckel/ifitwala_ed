# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_portfolio/student_portfolio.py

import frappe
from frappe import _
from frappe.model.document import Document


class StudentPortfolio(Document):
	def validate(self):
		self._set_context_defaults()
		self._set_title_default()
		self._validate_unique_per_year()
		self._validate_items()

	def _set_context_defaults(self):
		if self.school and not self.organization:
			self.organization = frappe.db.get_value("School", self.school, "organization")
		if not self.organization:
			frappe.throw(_("Organization is required."))

	def _set_title_default(self):
		if self.title:
			return
		self.title = f"Portfolio {self.academic_year}" if self.academic_year else _("Student Portfolio")

	def _validate_unique_per_year(self):
		if not (self.student and self.academic_year and self.school):
			return
		filters = {
			"student": self.student,
			"academic_year": self.academic_year,
			"school": self.school,
		}
		existing = frappe.db.get_value("Student Portfolio", filters, "name")
		if existing and existing != self.name:
			frappe.throw(_("A portfolio already exists for this student, school, and academic year."))

	def _validate_items(self):
		for row in self.items or []:
			references = [
				bool(row.task_submission),
				bool(row.student_reflection_entry),
				bool(row.artefact_file),
			]
			if sum(references) != 1:
				frappe.throw(_("Each portfolio item must reference exactly one evidence source."))

			if row.item_type == "Task Submission" and not row.task_submission:
				frappe.throw(_("Task Submission items must include a Task Submission reference."))
			if row.item_type == "Student Reflection Entry" and not row.student_reflection_entry:
				frappe.throw(_("Student Reflection Entry items must include a reflection reference."))
			if row.item_type == "External Artefact" and not row.artefact_file:
				frappe.throw(_("External Artefact items must include an artefact file."))

			if row.task_submission:
				task_student = frappe.db.get_value("Task Submission", row.task_submission, "student")
				if task_student and task_student != self.student:
					frappe.throw(_("Task Submission does not belong to the portfolio student."))

			if row.student_reflection_entry:
				reflection_student = frappe.db.get_value("Student Reflection Entry", row.student_reflection_entry, "student")
				if reflection_student and reflection_student != self.student:
					frappe.throw(_("Reflection entry does not belong to the portfolio student."))
