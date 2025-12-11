# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/reporting_cycle/reporting_cycle.py

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe import _


class ReportingCycle(Document):
	def validate(self):
		# Basic uniqueness: one cycle per (school, academic_year, term, program, name_label)
		if self.school and self.academic_year and self.term:
			filters = [
				["Reporting Cycle", "school", "=", self.school],
				["Reporting Cycle", "academic_year", "=", self.academic_year],
				["Reporting Cycle", "term", "=", self.term],
			]
			if self.program:
				filters.append(["Reporting Cycle", "program", "=", self.program])
			if self.name_label:
				filters.append(["Reporting Cycle", "name_label", "=", self.name_label])
			if self.name:
				filters.append(["Reporting Cycle", "name", "!=", self.name])

			exists = frappe.get_all("Reporting Cycle", filters=filters, limit=1)
			if exists:
				frappe.throw(
					_(
						"A Reporting Cycle with the same School, Academic Year, Term and Program/Name already exists ({0})."
					).format(exists[0].name)
				)

		# Soft guardrail
		if self.status == "Locked" and not self.teacher_edit_close:
			frappe.msgprint(
				_("Teacher edit window is not set but status is Locked."),
				indicator="orange",
			)

	@frappe.whitelist()
	def recalculate_course_results(self):
		frappe.enqueue(
			"ifitwala_ed.assessment.term_reporting.recalculate_course_term_results",
			reporting_cycle=self.name,
			queue="long",
		)
		return {"queued": True}


	@frappe.whitelist()
	def generate_student_reports(self):
		from ifitwala_ed.assessment import term_reporting

		return term_reporting.generate_student_term_reports(self.name)


def on_doctype_update():
	# Helpful for querying cycles by scope
	frappe.db.add_index("Reporting Cycle", ["school", "academic_year", "term", "program"])
