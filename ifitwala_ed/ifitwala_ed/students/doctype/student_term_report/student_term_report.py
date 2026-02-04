# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/student_term_report/student_term_report.py

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class StudentTermReport(Document):
	def before_save(self):
		# Keep header fields aligned with Program Enrollment if available
		if self.program_enrollment:
			pe = frappe.db.get_value(
				"Program Enrollment",
				self.program_enrollment,
				["program", "academic_year", "school"],
				as_dict=True,
			)
			if pe:
				self.program = pe.program
				self.academic_year = pe.academic_year
				self.school = pe.school

		# Auto-stamp finalisation metadata
		if self.status in ("Finalised", "Published") and not self.finalised_on:
			self.finalised_on = now_datetime()
			if not self.finalised_by:
				self.finalised_by = frappe.session.user


def on_doctype_update():
	frappe.db.add_index("Student Term Report", ["reporting_cycle", "student"])
