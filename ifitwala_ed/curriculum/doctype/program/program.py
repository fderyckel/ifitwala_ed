# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet

class Program(NestedSet):
	nsm_parent_field = "parent_program"

	def validate(self):
		self._validate_duplicate_course()
		self._validate_active_courses()

	def _validate_duplicate_course(self):
		seen = set()
		for row in self.courses:
			if row.course in seen:
				frappe.throw(_("Course {0} entered twice").format(row.course))
			seen.add(row.course)

	def _validate_active_courses(self):
		# Batch fetch statuses to minimize DB calls
		names = [r.course for r in (self.courses or []) if r.course]
		if not names:
			return

		rows = frappe.get_all("Course", filters={"name": ["in", names]}, fields=["name", "status"])
		status_by_name = {r.name: (r.status or "") for r in rows}

		inactive = []
		for row in self.courses or []:
			if not row.course:
				continue
			st = status_by_name.get(row.course, "")
			if st != "Active":
				inactive.append((row.idx, row.course, st or "Unknown"))

		if inactive:
			lines = "\n".join([f"Row {idx}: {name} (status: {st})" for idx, name, st in inactive])
			frappe.throw(_("Only Active Courses can be added:\n{0}").format(lines))
