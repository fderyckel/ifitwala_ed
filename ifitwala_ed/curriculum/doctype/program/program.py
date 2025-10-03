# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils.nestedset import get_descendants_of

class Program(NestedSet):

	def validate(self):
		self._validate_duplicate_course()

	def _validate_duplicate_course(self):
		seen = set()
		for row in self.courses:
			if row.course in seen:
				frappe.throw(_("Course {0} entered twice").format(row.course))
			seen.add(row.course)
