# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_attendance/student_attendance.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class StudentAttendance(Document):
	def validate(self):
		# Skip duplicate checks on bulk import
		if getattr(self.flags, "in_import", False):
			return

		# Whole-day rows: one per (student, date)
		if cint(self.whole_day):
			if not self.student or not self.attendance_date:
				frappe.throw(
					_("Student and Attendance Date are required for whole-day attendance."),
					title=_("Missing Required Fields"),
				)

			exists = frappe.db.exists(
				"Student Attendance",
				{
					"student": self.student,
					"attendance_date": self.attendance_date,
					"whole_day": 1,
					"name": ["!=", self.name],
				},
			)
			if exists:
				frappe.throw(
					_(
						"Daily attendance for student {0} on {1} already exists. "
						"Edit the existing record instead of creating a new one."
					).format(self.student, self.attendance_date),
					title=_("Duplicate Whole-Day Attendance"),
				)

		# Block-level rows: per (student, group, date, block)
		else:
			if frappe.db.exists(
				"Student Attendance",
				{
					"student": self.student,
					"student_group": self.student_group,
					"attendance_date": self.attendance_date,
					"block_number": self.block_number,
					"name": ["!=", self.name],
				},
			):
				frappe.throw(
					_("Attendance for this student, date, group, and block already exists."),
					title=_("Duplicate Attendance"),
				)

