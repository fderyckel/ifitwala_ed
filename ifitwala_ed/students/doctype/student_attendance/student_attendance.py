# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StudentAttendance(Document):
	def validate(self):
		# Prevent duplicate attendance for same student/date/group/block
		if self.flags.in_import:  # skip during data import
			return

		if frappe.db.exists(
			"Student Attendance",
			{
				"student": self.student,
				"student_group": self.student_group,
				"attendance_date": self.attendance_date,
				"block_number": self.block_number,
				"name": ["!=", self.name]
			}
		):
			frappe.throw(
				_("Attendance for this student, date, group, and block already exists."),
				title=_("Duplicate Attendance")
			)

