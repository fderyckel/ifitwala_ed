# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, date_diff


class StudentLog(Document):
	def validate(self):
		if self.requires_follow_up:
			if not self.follow_up_person:
				frappe.throw("Please select a follow-up person.")
			if not self.next_step:
				frappe.throw("Please select a next step.")
			if not self.follow_up_status:
				self.follow_up_status = "Open"
		else:
			# No follow-up required: status must be blank
			if self.follow_up_status:
				frappe.throw("Follow-up status must be blank if no follow-up is required.")
			self.follow_up_person = None
			self.next_step = None

		# Validate that the follow-up person has the role required for the next step
		expected_role = frappe.get_value("Student Log Next Step", self.next_step, "associated_role")
		has_role = False
		if expected_role:
				has_role = frappe.db.exists("Has Role", {
						"parent": self.follow_up_person, 
						"role": expected_role
				})
		if expected_role and not has_role:
				frappe.throw(_( 
						f"Follow-up person '{self.follow_up_person}' does not have the role '{expected_role}' required for this step."
				))


	def after_submit(self):
		if self.requires_follow_up and self.follow_up_person:
			if not self.follow_up_status:
				self.follow_up_status = "Open"
			self.create_follow_up_todo()

	def create_follow_up_todo(self):
		user = self.follow_up_person  # Already a Link to User

		if not user:
			return  # Safety guard

		# Create ToDo
		school = frappe.get_value("Program", self.program, "school")
		due_days = frappe.get_value("School", school, "default_follow_up_due_in_days") or 5
		todo = frappe.new_doc("ToDo")
		todo.update({
			"owner": user,
			"allocated_to": user,
			"assigned_by": frappe.session.user,
			"reference_type": self.doctype,
			"reference_name": self.name,
			"description": f"Follow up on Student Log for {self.student_name}",
			"date": frappe.utils.add_days(frappe.utils.today(), due_days), 
			"priority": "Medium",
			"color": "#ffcd59",  # friendly yellow
		})
		todo.insert(ignore_permissions=True)

		# Log comment for traceability
		self.add_comment(
			comment_type="Comment",
			text=_("ToDo assigned to {user} for follow-up.").format(user=user)
		)


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
			AND %s BETWEEN ay.year_start_date AND ay.year_end_date
		ORDER BY ay.year_start_date DESC
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
