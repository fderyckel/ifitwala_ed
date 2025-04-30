# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, date_diff


class StudentLog(Document):
	def on_submit(self):
		if self.requires_follow_up and self.follow_up_person:
			self.create_follow_up_todo()
	
	def after_submit(self):
		if self.requires_follow_up and self.follow_up_status == "Open" and self.follow_up_person:
			user = frappe.db.get_value("Employee", self.follow_up_person, "user_id")
			if user:
				frappe.get_doc({
					"doctype": "Comment",
					"comment_type": "Info",
					"reference_doctype": self.doctype,
					"reference_name": self.name,
					"content": f"ToDo assigned to {user} for follow-up.",
				}).insert(ignore_permissions=True)


	def create_follow_up_todo(self):
		user = frappe.db.get_value("Employee", self.follow_up_person, "user_id")
		if user:
			todo = frappe.new_doc("ToDo")
			todo.update({
				"owner": user,
				"assigned_by": frappe.session.user,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"description": f"Follow up on Student Log for {self.student_name}",
				"date": frappe.utils.add_days(frappe.utils.today(), 2),
				"priority": "Medium"
			})
			todo.insert(ignore_permissions=True)

@frappe.whitelist()
def get_employee_data(employee_name=None):
	"""
	If employee_name is given, return that employee's details.
	Otherwise, return the current user's employee details.
	"""
	if employee_name:
		employee = frappe.db.get_value("Employee",
			{"name": employee_name},
			["name", "employee_full_name"],
			as_dict=True
		)
	else:
		# If no employee_name, use session user
		employee = frappe.db.get_value("Employee",
			{"user_id": frappe.session.user},
			["name", "employee_full_name"],
			as_dict=True
		)

	return employee or {}

@frappe.whitelist()
def get_active_program_enrollment(student):
	if not student:
		return {}

	today = frappe.utils.today()

	pe = frappe.db.sql("""
		SELECT
			pe.name, pe.program, pe.academic_year
		FROM
			`tabProgram Enrollment` pe
		JOIN
			`tabAcademic Year` ay ON pe.academic_year = ay.name
		WHERE
			pe.student = %s
			AND %s BETWEEN pe.enrollment_date AND ay.year_end_date
		ORDER BY pe.modified DESC
		LIMIT 1
	""", (student, today), as_dict=True)

	return pe[0] if pe else {}

@frappe.whitelist()
def get_follow_up_role_from_next_step(next_step):
	return frappe.get_value("Student Log Next Step", next_step, "frappe_role")

# for scheduler events. 
def auto_close_completed_logs():
	today = frappe.utils.today()

	# Find completed logs with auto-close setting
	logs = frappe.get_all("Student Log", filters={
		"follow_up_status": "Completed",
		"auto_close_after_days": [">", 0],
	}, fields=["name", "modified", "auto_close_after_days"])

	for log in logs:
		last_updated = get_datetime(log.modified)
		if date_diff(today, last_updated.date()) >= log.auto_close_after_days:
			frappe.get_doc("Student Log", log.name).db_set("follow_up_status", "Closed")
			frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Student Log",
				"reference_name": log.name,
				"content": f"Auto-closed after {log.auto_close_after_days} days of inactivity."
			}).insert(ignore_permissions=True)
