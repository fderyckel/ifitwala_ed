# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowtime, today

class StudentPatientVisit(Document):
	def validate(self):
		self.set_school()

	def set_school(self):
		if self.school: return

		student = frappe.db.get_value("Student Patient", self.student_patient, "student")
		if not student: return

		anchor_school = frappe.db.get_value("Student", student, "anchor_school")
		if anchor_school:
			self.school = anchor_school

	def on_submit(self):
		pass

@frappe.whitelist()
def get_student_school(student_patient, date=None):
	# date argument is kept for compatibility but not used for anchor_school
	student = frappe.db.get_value("Student Patient", student_patient, "student")
	if not student: return None

	return frappe.db.get_value("Student", student, "anchor_school")


