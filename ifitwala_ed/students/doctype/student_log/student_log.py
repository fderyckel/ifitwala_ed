# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, date_diff, cint

# Try native assign/remove; fall back to direct ToDo updates if unavailable
try:
	from frappe.desk.form.assign_to import add as assign_add, remove as assign_remove
except Exception:
	assign_add = None
	assign_remove = None


class StudentLog(Document):
	# ---------------------------------------------------------------------
	# Status & timeline helpers
	# ---------------------------------------------------------------------
	def _compose_status_change(self, old, new, reason=None):
		if old == new:
			return None
		msg = f"Follow-up status: {old or '—'} → {new or '—'}"
		if reason:
			msg += f" ({reason})"
		return msg

	def _cache_status_comment(self, msg):
		"""Cache one status-change message during validate; flush after save."""
		if msg:
			self.flags._status_change_msg = msg

	def _write_cached_status_comment_if_any(self):
		"""Flush the cached message now that the doc exists in DB."""
		msg = getattr(self.flags, "_status_change_msg", None)
		if not msg:
			return
		try:
			self.add_comment("Info", _(msg))
		finally:
			self.flags._status_change_msg = None  # prevent duplicates

	def _apply_status(self, new_status, reason=None, write_immediately=False):
		"""
		Update status and (optionally) log a concise timeline comment.
		"""
		# Read previous safely (DB for existing, in-memory for new)
		prev = (
			frappe.db.get_value(self.doctype, self.name, "follow_up_status")
			if self.name and not self.is_new()
			else self.follow_up_status
		)

		# No-op if nothing changes
		if prev == new_status:
			# still normalize in-memory for new docs
			if self.is_new():
				self.follow_up_status = new_status
			return

		# Apply the new status
		if self.is_new():
			self.follow_up_status = new_status
		else:
			self.db_set("follow_up_status", new_status)

		# Decide whether to emit a comment
		reason_key = (reason or "").strip().lower()
		suppress_reasons = {"recomputed on validate", "(re)assignment"}
		if reason_key in suppress_reasons:
			return  # quiet update; no timeline comment

		# Compose and emit (deferred or immediate)
		msg = f"Follow-up status: {prev or '—'} → {new_status or '—'}"
		if reason:
			msg += f" ({reason})"

		if write_immediately and not self.is_new():
			try:
				self.add_comment("Info", _(msg))
			except Exception:
				pass
		else:
			self._cache_status_comment(msg)


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
		Pre-submit assignment support:
		- If requires_follow_up = 1 and follow_up_person is set before submit,
			ensure exactly one open ToDo exists for that user (single-assignee policy).
		- Enforce role from Next Step → associated_role (if provided).
		- Mirror current open assignee back to follow_up_person.
		- Derive and cache status (timeline cleanup is deferred to Change #2).
		"""
		if cint(self.requires_follow_up):
			if not self.next_step:
				frappe.throw(_("Please select a next step."))

			# Use 'associated_role' (per your Next Step JSON)
			expected_role = None
			if self.next_step:
				expected_role = frappe.get_value("Student Log Next Step", self.next_step, "associated_role")

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

			# Role guard if both next_step role and person exist
			if expected_role and self.follow_up_person:
				has_role = frappe.db.exists("Has Role", {"parent": self.follow_up_person, "role": expected_role})
				if not has_role:
					frappe.throw(_(f"Follow-up person '{self.follow_up_person}' does not have required role '{expected_role}'."))

		else:
			# Follow-up not required → clear & close
			had_status = self.follow_up_status
			self._unassign()
			self.follow_up_person = None
			self.next_step = None
			if had_status:
				self._apply_status(None, reason="follow-up disabled", write_immediately=False)
			else:
				self.follow_up_status = None

		# Derive & cache status (prevents client from fighting it)
		derived = self._compute_follow_up_status()
		self._apply_status(derived, reason="recomputed on validate", write_immediately=False)


	def on_submit(self):
		"""
		Submission invariants for the Student Log itself:
		- If requires_follow_up = 1, exactly one open assignment must exist.
		- Mirror that assignee into follow_up_person.
		- Recompute status; timeline comment is suppressed via _apply_status() reason.
		"""
		if not cint(self.requires_follow_up):
			return

		opens = self._open_assignees()

		# Edge case: creator picked follow_up_person pre-submit but no assignment exists yet
		if not opens and self.follow_up_person:
			self._assign_to(self.follow_up_person)
			opens = self._open_assignees()

		if len(opens) != 1:
			frappe.throw(_("Exactly one assignee is required before submit."))

		self.follow_up_person = opens[0]
		self._apply_status(self._compute_follow_up_status(), reason="on submit", write_immediately=False)



	def after_save(self):
		# Handle updates as well (idempotent via clearing the flag)
		self._write_cached_status_comment_if_any()

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
	"""
	Return the role associated with the selected Next Step.
	Used to role-filter the follow_up_person picker (pre-submit assignment).
	"""
	return frappe.get_value("Student Log Next Step", next_step, "associated_role")



# ---------- assign/reassign endpoint (owner OR Academic Admin OR current assignee) ----------
@frappe.whitelist()
def assign_follow_up(log_name: str, user: str):
	log = frappe.get_doc("Student Log", log_name)

	# Permission: author, Academic Admin, or current assignee may (re)assign
	roles = set(frappe.get_roles())
	is_admin = "Academic Admin" in roles
	is_author = (frappe.session.user == log.owner)
	current = frappe.db.get_value(
		"ToDo",
		{"reference_type": "Student Log", "reference_name": log.name, "status": "Open"},
		"allocated_to"
	)
	allowed = is_admin or is_author or (current and current == frappe.session.user)
	if not allowed:
		frappe.throw(_("Not permitted to (re)assign this Student Log."))

	# Previous single open assignee (for clear "Old → New" message)
	prev_rows = frappe.get_all(
		"ToDo",
		filters={"reference_type": log.doctype, "reference_name": log.name, "status": "Open"},
		fields=["allocated_to"]
	)
	prev_user = prev_rows[0].allocated_to if len(prev_rows) == 1 else None

	# Clear existing opens (single-assignee policy)
	for r in prev_rows:
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

	# Create new assignment (native API preferred)
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

	# Mirror and recompute status (comment suppressed by reason="(re)assignment")
	log.db_set("follow_up_person", user)
	log._apply_status(log._compute_follow_up_status(), reason="(re)assignment", write_immediately=True)

	# Timeline policy:
	# - With native assign_add: rely on Frappe's "Assigned to ..." for initial assign;
	#   only add a comment when it's a true reassignment Old → New.
	# - Without assign_add (fallback): emit a single concise comment ourselves.
	if assign_add:
		if prev_user and prev_user != user:
			log.add_comment(
				"Info",
				_("Reassigned: {0} → {1}").format(log._fullname(prev_user), log._fullname(user))
			)
	else:
		# Fallback environment: add exactly one comment
		if prev_user and prev_user != user:
			msg = _("Reassigned: {0} → {1}").format(log._fullname(prev_user), log._fullname(user))
		else:
			msg = _("Assigned to {0}").format(log._fullname(user))
		log.add_comment("Info", msg)

	return {"ok": True, "assigned_to": user}



@frappe.whitelist()
def finalize_close(log_name: str):
	log = frappe.get_doc("Student Log", log_name)

	roles = set(frappe.get_roles())
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

	# Apply status + timeline immediately (outside save lifecycle)
	log._apply_status("Closed", reason="manual finalize", write_immediately=True)
	return {"ok": True, "status": "Closed"}


# ---------- scheduler: Completed → Closed ----------
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
			doc._apply_status("Closed", reason=f"auto-closed after {row.auto_close_after_days} days of inactivity", write_immediately=True)
			# Optional extra audit note
			try:
				frappe.get_doc({
					"doctype": "Comment",
					"comment_type": "Info",
					"reference_doctype": "Student Log",
					"reference_name": row.name,
					"content": f"Auto-closed after {row.auto_close_after_days} days of inactivity."
				}).insert(ignore_permissions=True)
			except Exception:
				pass
