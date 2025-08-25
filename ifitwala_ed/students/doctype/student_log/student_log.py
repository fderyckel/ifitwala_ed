# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, date_diff, cint

# NEW: try native assign/remove (fallback to ToDo-close if unavailable)
try:
	from frappe.desk.form.assign_to import add as assign_add, remove as assign_remove
except Exception:
	assign_add = None
	assign_remove = None


class StudentLog(Document):
	# ---------------------------------------------------------------------
	# Timeline / status helpers
	# ---------------------------------------------------------------------
	def _log_status_change(self, old, new, reason=None):
		if old == new:
			return
		msg = f"Follow-up status: {old or '—'} → {new or '—'}"
		if reason:
			msg += f" ({reason})"
		self.add_comment("Info", _(msg))

	def _apply_status(self, new_status, reason=None):
		"""Set cached status + write a timeline entry if it changed."""
		prev = (
			frappe.db.get_value(self.doctype, self.name, "follow_up_status")
			if self.name and not self.is_new()
			else self.follow_up_status
		)
		if self.is_new():
			self.follow_up_status = new_status
		else:
			self.db_set("follow_up_status", new_status)
		self._log_status_change(prev, new_status, reason)

	def _compute_follow_up_status(self):
		"""
		Derive status from DB state (single source of truth):
		  - None when follow-up not required
		  - 'Completed' if any submitted Follow Up exists
		  - 'In Progress' if any Follow Up (draft/saved) exists
		  - 'Open' if exactly one open ToDo exists
		  - None otherwise
		"""
		if not cint(self.requires_follow_up) or not self.name:
			return None

		# 1) Any submitted follow-up? → Completed
		if frappe.db.exists("Student Log Follow Up", {"student_log": self.name, "docstatus": 1}):
			return "Completed"

		# 2) Any follow-up saved/draft? → In Progress
		if frappe.db.exists("Student Log Follow Up", {"student_log": self.name}):
			return "In Progress"

		# 3) Check assignment: single open assignee → Open
		open_assignees = frappe.get_all(
			"ToDo",
			filters={"reference_type": "Student Log", "reference_name": self.name, "status": "Open"},
			limit=2
		)
		return "Open" if len(open_assignees) == 1 else None

	# ---------------------------------------------------------------------
	# Lifecycle
	# ---------------------------------------------------------------------
	def validate(self):
		"""
		State machine:
		- requires_follow_up = 0 ⇒ status NULL, clear assignees, clear follow_up_person/next_step
		- requires_follow_up = 1 ⇒ next_step required; single open assignee expected by submit
		"""
		if cint(self.requires_follow_up):
			if not self.next_step:
				frappe.throw(_("Please select a next step."))

			# Enforce 'frappe_role' from Next Step (if set) on chosen follow_up_person
			expected_role = None
			if self.next_step:
				expected_role = frappe.get_value("Student Log Next Step", self.next_step, "frappe_role")

			# If a person is chosen pre-submit, ensure ToDo reflects that (single open)
			if self.follow_up_person:
				opens = self._open_assignees()
				if not opens:
					self._assign_to(self.follow_up_person)
				elif opens != [self.follow_up_person]:
					self._unassign()
					self._assign_to(self.follow_up_person)

			# Mirror current open assignee → follow_up_person
			current = self._current_assignee()
			self.follow_up_person = current or self.follow_up_person

			if expected_role and self.follow_up_person:
				has_role = frappe.db.exists("Has Role", {"parent": self.follow_up_person, "role": expected_role})
				if not has_role:
					frappe.throw(_(f"Follow-up person '{self.follow_up_person}' does not have required role '{expected_role}'."))

		else:
			# Follow-up not required → clear + close assignments; log transition if needed
			had_status = self.follow_up_status
			self._unassign()
			self.follow_up_person = None
			self.next_step = None
			if had_status:
				self._apply_status(None, reason="follow-up disabled")
			else:
				self.follow_up_status = None

		# Derive & cache status (prevents client from fighting it)
		derived = self._compute_follow_up_status()
		self._apply_status(derived, reason="recomputed on validate")

	def on_submit(self):
		# Guard: exactly one assignee when follow-up is required
		if cint(self.requires_follow_up):
			opens = self._open_assignees()
			if len(opens) != 1:
				frappe.throw(_("Exactly one assignee is required before submit."))
			self.follow_up_person = opens[0]
			self._apply_status(self._compute_follow_up_status(), reason="on submit")

	# ---------------------------------------------------------------------
	# Assignment helpers
	# ---------------------------------------------------------------------
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


# ---------- NEW: assign/reassign endpoint (policy: owner OR Academic Admin OR current assignee) ----------
@frappe.whitelist()
def assign_follow_up(log_name: str, user: str):
	log = frappe.get_doc("Student Log", log_name)

	roles = set(frappe.get_roles())  # current session user
	is_admin = "Academic Admin" in roles

	# Server-side: treat the document owner as the canonical "author"
	is_author = (frappe.session.user == log.owner)

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
	log._apply_status(log._compute_follow_up_status(), reason="(re)assignment")
	log.add_comment("Comment", _("(Re)assigned to {0}").format(frappe.utils.get_fullname(user) or user))
	return {"ok": True, "assigned_to": user}


@frappe.whitelist()
def finalize_close(log_name: str):
	log = frappe.get_doc("Student Log", log_name)

	roles = set(frappe.get_roles())  # current session user
	is_admin = "Academic Admin" in roles
	is_owner = (frappe.session.user == log.owner)

	if not (is_admin or is_owner):
		frappe.throw(_("Only Academic Admin or the author of the note can finalize (close) this log."))

	# Must be in Completed before closing (keeps the flow clean)
	if (log.follow_up_status or "").lower() != "completed":
		frappe.throw(_("Log must be in 'Completed' status before it can be finalized (Closed)."))

	# If it's already Closed, no-op (idempotent)
	if (log.follow_up_status or "").lower() == "closed":
		return {"ok": True, "status": "Closed"}

	# Apply status via helper so the timeline gets a proper entry
	log._apply_status("Closed", reason="manual finalize")
	return {"ok": True, "status": "Closed"}

# ---------- FIX: scheduler: Completed → Closed ----------
def auto_close_completed_logs():
	"""
	Daily job: move 'Completed' → 'Closed' after N days (N pulled from each log's auto_close_after_days).
	"""
	today = frappe.utils.today()

	logs = frappe.get_all(
		"Student Log",
		filters={"follow_up_status": "Completed", "auto_close_after_days": [">", 0]},
		fields=["name", "modified", "auto_close_after_days"]
	)

	for row in logs:
		last_updated = get_datetime(row.modified)
		if date_diff(today, last_updated.date()) >= row.auto_close_after_days:
			doc = frappe.get_doc("Student Log", row.name)
			doc._apply_status("Closed", reason=f"auto-closed after {row.auto_close_after_days} days of inactivity")
			# Optional: keep your explicit info comment (nice audit trail)
			frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Student Log",
				"reference_name": row.name,
				"content": f"Auto-closed after {row.auto_close_after_days} days of inactivity."
			}).insert(ignore_permissions=True)
