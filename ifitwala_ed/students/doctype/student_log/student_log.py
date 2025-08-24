# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, date_diff

# NEW: try native assign/remove, safe-fallback to closing ToDo
try:
	from frappe.desk.form.assign_to import add as assign_add, remove as assign_remove
except Exception:
	assign_add = None
	assign_remove = None


class StudentLog(Document):
	def validate(self):
		# requires_follow_up gate
		if self.requires_follow_up:
			if not self.next_step:
				frappe.throw(_("Please select a next step."))
			# status defaulting
			if not self.follow_up_status or self.follow_up_status == "Closed":
				self.follow_up_status = "Open"
			# mirror current assignment → follow_up_person (read-only field in UI)
			user = self._current_assignee()
			self.follow_up_person = user or None
		else:
			# clear follow-up fields if not required
			self.follow_up_person = None
			self.next_step = None
			self.follow_up_status = None  # blank/None means no follow-up

		# (kept) role validation when next_step has an expected role
		if self.requires_follow_up and self.next_step:
			expected_role = frappe.get_value("Student Log Next Step", self.next_step, "associated_role")
			if expected_role and self.follow_up_person:
				has_role = frappe.db.exists("Has Role", {"parent": self.follow_up_person, "role": expected_role})
				if not has_role:
					frappe.throw(_(
						f"Follow-up person '{self.follow_up_person}' lacks required role '{expected_role}'."
					))

	def on_submit(self):
		# If a follow-up is required, ensure exactly ONE assignee exists; otherwise create it
		if self.requires_follow_up:
			assignees = self._open_assignees()
			if len(assignees) == 0:
				# create from follow_up_person if present; otherwise block submission
				user = self.follow_up_person
				if not user:
					frappe.throw(_("Please assign a follow-up (use the Assign Follow-Up button) before submitting."))
				self._assign_to(user)
				self.add_comment("Assignment", _("Assigned to {0} for follow-up.").format(self._fullname(user)))
				self.follow_up_status = "Open"
			elif len(assignees) > 1:
				frappe.throw(_("Exactly one assignee is allowed. Please resolve multiple assignments."))
			else:
				# keep status in sync and mirror field
				self.follow_up_person = assignees[0]
				self.follow_up_status = "Open"

	# NEW: helper — assign with due date by School setting
	def _assign_to(self, user: str):
		if not user:
			return
		due_days = 5
		if self.program:
			school = frappe.get_value("Program", self.program, "school")
			if school:
				due_days = frappe.get_value("School", school, "default_follow_up_due_in_days") or 5
		due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))

		if assign_add:
			assign_add({
				"doctype": self.doctype,
				"name": self.name,
				"assign_to": [user],
				"description": f"Follow up on Student Log for {self.student_name}",
				"due_date": due_date
			})
		else:
			# fallback: create a native ToDo (still 'native' representation of assignment)
			todo = frappe.new_doc("ToDo")
			todo.update({
				"owner": user,
				"allocated_to": user,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"description": f"Follow up on Student Log for {self.student_name}",
				"date": due_date,
				"status": "Open",
				"priority": "Medium",
			})
			todo.insert(ignore_permissions=True)

	# NEW: helper — remove/close current assignment
	def _unassign(self, user: str | None = None):
		assignees = self._open_assignees()
		targets = [user] if user else assignees
		for u in targets:
			if assign_remove:
				assign_remove(self.doctype, self.name, u)
			else:
				frappe.db.set_value(
					"ToDo",
					{"reference_type": self.doctype, "reference_name": self.name, "allocated_to": u, "status": "Open"},
					"status",
					"Closed"
				)

	# NEW: helper — fetch single open assignee (if any)
	def _current_assignee(self) -> str | None:
		users = self._open_assignees()
		return users[0] if users else None

	def _open_assignees(self) -> list[str]:
		rows = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": self.doctype,
				"reference_name": self.name,
				"status": "Open"
			},
			fields=["allocated_to"]
		)
		return [r.allocated_to for r in rows]

	# (kept) auto-close job — unchanged
