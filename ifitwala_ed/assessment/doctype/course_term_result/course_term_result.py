# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/course_term_result/course_term_result.py

from __future__ import annotations

import frappe
from frappe.model.document import Document


class CourseTermResult(Document):
	def validate(self):
		# Keep override flag in sync
		self.is_override = 1 if self.override_grade_value else 0


def on_doctype_update():
	# Optimise the common lookups used by term_reporting
	frappe.db.add_index("Course Term Result", ["reporting_cycle", "student"])
	frappe.db.add_index("Course Term Result", ["reporting_cycle", "program_enrollment", "course"])
