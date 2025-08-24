# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, date_diff

# NEW: try native assign/remove (fallback to ToDo-close if unavailable)
try:
	from frappe.desk.form.assign_to import add as assign_add, remove as assign_remove
except Exception:
	assign_add = None
	assign_remove = None


class StudentLog(Document):
	def validate(self):
		# KEPT: your original gate, but mirror assignment → follow_up_person and status
		if self.requires_follow_up:
			if not self.next_step:
				frappe.throw(_("Please select a next step."))
			if not self.follow_up_status or self.follow_up_status == "Closed":
				self.follow_up_status = "Open"

			# Validate role from Next Step (uses 'associated_role' per your earlier code)
			expected_role = None
			if self.next_step:
				expected_role = frappe.get_value("Student Log Next Step", self.next_step, "associated_role")

			# Mirror current assignee to follow_up_person (read-only in UI/list filters)
			current = self._current_assignee()
			self.follow_up_person = current or self.follow_up_person

			if expected_role and self.follow_up_person:
				has_role = frappe.db.exists("Has Role", {"parent": self.follow_up_person, "role": expected_role})
				if not has_role:
					frappe.throw(_(
						f"Follow-up person '{self.follow_up_person}' does not have required role '{expected_role}'."
					))
		else:
			# No follow-up required → clear fields and leave status blank
			if self.follow_up_status:
				frappe.throw(_("Follow-up status must be blank if no follow-up is required."))
			self.follow_up_person = None
			self.next_step = None

	def on_submit(self):
		# NEW: enforce exactly-one native assignment when follow-up is required
		if self.requires_follow_up:
			open_assignees = self._open_assignees()
			if len(open_assignees) == 0:
				# create from chosen follow_up_person, if any; otherwise block
				if not self.follow_up_person:
					frappe.throw(_("Please assign a follow-up (use Assign Follow-Up) before submitting."))
				self._assign_to(self.follow_up_person)
				self.add_comment("Comment", _("Assigned to {0} for follow-up.").format(self._fullname(self.follow_up_person)))
				self.follow_up_status = "Open"
			elif len(open_assignees) > 1:
				frappe.throw(_("Exactly one assignee is allowed. Please resolve multiple assignments."))
			else:
				# keep mirror
				self.follow_up_person = open_assignees[0]
				self.follow_up_status = "Open"

	# ---------- helpers (NEW) ----------
	def _assign_to(self, user):
		if not user:
			return
		# due date from School.default_follow_up_due_in_days (fallback 5)
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
			# fallback to native ToDo doc (same underlying model)
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

	def _unassign(self, user=None):
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

	def _current_assignee(self):
		users = self._open_assignees()
		return users[0] if users else None

	def _open_assignees(self):
		rows = frappe.get_all(
			"ToDo",
			filters={"reference_type": self.doctype, "reference_name": self.name, "status": "Open"},
			fields=["allocated_to"]
		)
		return [r.allocated_to for r in rows]

	def _fullname(self, user):
		return frappe.utils.get_fullname(user) or user


# ---------- WHITELISTED HELPERS (KEPT) ----------
@frappe.whitelist()
def get_employee_data(employee_name=None):
	"""
	If employee_name is given, return that employee's details.
	Otherwise, return the current user's employee details.
	"""
	if employee_name:
		employee = frappe.db.get_value(
			"Employee",
			{"name": employee_name},
			["name", "employee_full_name"],
			as_dict=True
		)
	else:
		employee = frappe.db.get_value(
			"Employee",
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


# ---------- NEW: assign/reassign endpoint (policy: author OR Academic Admin OR current assignee) ----------
@frappe.whitelist()
def assign_follow_up(log_name: str, user: str):
	log = frappe.get_doc("Student Log", log_name)

	is_admin = frappe.has_role("Academic Admin")
	is_author = (frappe.session.user_fullname == (log.author_name or ""))
	current = frappe.db.get_value(
		"ToDo",
		{"reference_type": "Student Log", "reference_name": log.name, "status": "Open"},
		"allocated_to"
	)
	allowed = is_admin or is_author or (current and current == frappe.session.user)
	if not allowed:
		frappe.throw(_("Not permitted to (re)assign this Student Log."))

	# clear existing opens (single policy)
	rows = frappe.get_all(
		"ToDo",
		filters={"reference_type": log.doctype, "reference_name": log.name, "status": "Open"},
		fields=["allocated_to"]
	)
	for r in rows:
		try:
			if assign_remove:
				assign_remove(log.doctype, log.name, r.allocated_to)
			else:
				frappe.db.set_value(
					"ToDo",
					{"reference_type": log.doctype, "reference_name": log.name, "allocated_to": r.allocated_to, "status": "Open"},
					"status",
					"Closed"
				)
		except Exception:
			pass

	# add new assignment
	due_days = 5
	if log.program:
		school = frappe.get_value("Program", log.program, "school")
		if school:
			due_days = frappe.get_value("School", school, "default_follow_up_due_in_days") or 5
	due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))

	if assign_add:
		assign_add({
			"doctype": log.doctype,
			"name": log.name,
			"assign_to": [user],
			"description": f"Follow up on Student Log for {log.student_name}",
			"due_date": due_date
		})
	else:
		todo = frappe.new_doc("ToDo")
		todo.update({
			"owner": user,
			"allocated_to": user,
			"reference_type": log.doctype,
			"reference_name": log.name,
			"description": f"Follow up on Student Log for {log.student_name}",
			"date": due_date,
			"status": "Open",
			"priority": "Medium",
		})
		todo.insert(ignore_permissions=True)

	# mirror + status + timeline
	log.db_set("follow_up_person", user)
	if log.requires_follow_up and (not log.follow_up_status or log.follow_up_status == "Closed"):
		log.db_set("follow_up_status", "Open")
	log.add_comment("Comment", _("(Re)assigned to {0}").format(frappe.utils.get_fullname(user) or user))
	return {"ok": True, "assigned_to": user}


# ---------- FIX: restore your scheduler job ----------
def auto_close_completed_logs():
	"""
	Daily job: move 'Completed' → 'Closed' after N days (N pulled from each log's auto_close_after_days).
	NOTE: This matches your previous implementation so existing hooks keep working.
	"""
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
