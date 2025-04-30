# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StudentLogFollowUp(Document):
	def after_save(self):
		log = frappe.get_doc("Student Log", self.student_log)
		if log.follow_up_status == "Open":
			log.db_set("follow_up_status", "In Progress")

	def after_submit(self):
		log = frappe.get_doc("Student Log", self.student_log)

		if log.follow_up_status not in ("Closed",):
			log.db_set("follow_up_status", "Completed")

		# Get auto-close config from Next Step
		if log.next_step:
			auto_close_days = frappe.db.get_value("Student Log Next Step", log.next_step, "auto_close_after_days")
			if auto_close_days:
				log.db_set("auto_close_after_days", auto_close_days)

