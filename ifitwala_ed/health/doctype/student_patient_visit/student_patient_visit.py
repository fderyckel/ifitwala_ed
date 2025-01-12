# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowtime

class StudentPatientVisit(Document):
	def on_submit(self):
		self.create_student_log()

	def create_student_log(self):
		student_name = frappe.db.get_value("Student Patient", self.student_patient, "student")
		student_full_name = frappe.db.get_value("Student", student_name, "student_full_name")
		author_full_name = frappe.get_value("User", frappe.session.user, "full_name")

		log_en = frappe.get_doc({
			"doctype": "Student Log",
			"student": student_name,
			"date": self.date,
			"time": nowtime(),
			"log_type": "Medical", 
			"next_step": "For information only", 
			"author": author_full_name,
			"log": f"Today between {self.time_of_arrival} and {self.time_of_discharge}, {student_full_name} visited the health office. Reason: {self.note}",
			"docstatus": 1
		})

		log_en.insert(ignore_permissions=True) # Use insert() instead of save() for new documents
		log_en.submit()


