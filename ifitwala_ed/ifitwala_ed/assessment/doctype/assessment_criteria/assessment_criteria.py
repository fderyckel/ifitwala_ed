# Copyright (c) 2024, François de Ryckek and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/assessment_criteria/assessment_criteria.py

import frappe
from frappe.model.document import Document
from frappe import _

STD_CRITERIA = ["total", "total score", "total grade", "maximum score", "score", "grade"]

class AssessmentCriteria(Document):
	def autoname(self):
		"""Generate a stable code for this criteria.

		- If course_group or abbr is set: Crit-<course_group>-<abbr>
		- Else: CRIT-<two-letter abbreviations from each word in assessment_criteria>
		"""
		if self.course_group or self.abbr:
			title_parts = ["Crit"]
			if self.course_group:
				title_parts.append(self.course_group)
			if self.abbr:
				title_parts.append(self.abbr)
			code = "-".join(title_parts)
		else:
			words = (self.assessment_criteria or "").split()
			abbreviation = "".join(word[:2].capitalize() for word in words) or "GEN"
			code = f"CRIT-{abbreviation}"

		# Use the same code for name and hidden title
		self.name = code
		self.title = code

	def validate(self):
		# Prevent reserved / garbage criteria names
		if (self.assessment_criteria or "").strip().lower() in STD_CRITERIA:
			frappe.throw(_("These are reserved Key words. Please rename the criteria"))


