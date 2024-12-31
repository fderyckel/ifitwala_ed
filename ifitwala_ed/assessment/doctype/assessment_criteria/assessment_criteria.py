# Copyright (c) 2024, François de Ryckek and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

STD_CRITERIA = ["total", "total score", "total grade", "maximum score", "score", "grade"]

class AssessmentCriteria(Document):  
	
	def validate(self):
		if self.assessment_criteria.lower() in STD_CRITERIA:
			frappe.throw(_("These are reserved Key words. Please rename the criteria"))
		
		if self.course_group or self.abbr: 
			title_parts = ["Crit"]
			if self.course_group:
				title_parts.append(self.course_group)
			if self.abbr:
				title_parts.append(self.abbr)
			self.title = "-".join(title_parts)
		else:
			words = self.assessment_criteria.split()
			abbreviation = "".join(word[:2].capitalize() for word in words)
			self.title = f"CRIT-{abbreviation}"


