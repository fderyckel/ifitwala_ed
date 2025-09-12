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


	def _apply_status(self, new_status, reason=None, write_immediately=False):
		"""
		Update status and (optionally) log a concise timeline comment.

		No caching: comments are added immediately when the doc exists; skipped on new docs.
		Suppresses comment spam for:
		- 'recomputed on validate'
		- '(re)assignment'
		- 'on submit'
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
		if reason_key in {"recomputed on validate", "(re)assignment", "on submit"}:
			return  # quiet update; no timeline comment

		# If the doc doesn't exist yet, skip timeline (no cache)
		if self.is_new():
			return

		# Compose and emit immediately
		msg = f"Follow-up status: {prev or '—'} → {new_status or '—'}"
		if reason:
			msg += f" ({reason})"
		try:
			self.add_comment("Info", _(msg))
		except Exception:
			pass

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
		- Derive status timeline comments suppressed for auto reasons).
		"""
		if cint(self.requires_follow_up):
			if not self.next_step:
				frappe.throw(_("Please select a next step."))

			# Use 'associated_role' (per your Next Step JSON)
			expected_role = None
			if self.next_step:
				expected_role = frappe.get_value("Student Log Next Step", self.next_step, "associated_role")

			# If a person is chosen pre-submit, ensure ToDo reflects that (single open)
			if self.follow_up_person and not self.is_new():
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

		if not self.school and self.program:
			self.school = frappe.db.get_value("Program", self.program, "school")

		self._assert_followup_transition_and_immutability()

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

	# ---------------------------------------------------------------------
	# Validation helpers
	# ---------------------------------------------------------------------
	def _assert_followup_transition_and_immutability(self):
			"""Enforce legal status transitions and lock core fields once Closed."""
			old = self.get_doc_before_save() or frappe._dict()

			old_status = (old.get("follow_up_status") or "").lower()
			new_status = (self.follow_up_status or "").lower()

			# Allowed transitions (None means previously empty)
			allowed = {
					None: {"", "open"},
					"": {"open"},
					"open": {"open", "in progress", "completed"},
					"in progress": {"in progress", "completed"},
					"completed": {"completed", "closed"},
					"closed": {"closed"},  # no further changes
			}

			# Normalize None/empty
			old_key = old_status if old_status else ("")
			if old_key == "":
					old_key = None

			if old_key not in allowed or new_status not in allowed[old_key]:
					# Permit no-change (e.g., saving without touching status)
					if new_status != old_status:
							frappe.throw(
									_("Illegal follow-up status change: {0} → {1}")
									.format(old_status or "None", new_status or "None"),
									title=_("Invalid Transition")
							)

			# Once Closed, lock core follow-up fields
			if (old_status == "closed") or (new_status == "closed" and old_status != "closed"):
					# If already closed before this save OR moving to closed now, ensure no core fields change afterward
					locked_fields = {
							"requires_follow_up",
							"next_step",
							"follow_up_role",
							"follow_up_person",
							"program",          # optional: protect context
							"academic_year",    # optional: protect context
					}
					for f in locked_fields:
							if old.get(f) != self.get(f):
									frappe.throw(
											_("Field {0} cannot be changed after the log is Closed.").format(f),
											title=_("Locked After Close")
									)

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

	def on_doctype_update():
			frappe.db.add_index("Student Log", ["school"])

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
	sl = frappe.get_doc("Student Log", log_name)

	# 🚫 already-closed guard (you added earlier)
	if (sl.follow_up_status or "").lower() == "closed":
		frappe.throw(
			_("This Student Log is already closed and cannot be (re)assigned."),
			title=_("Follow-Up Closed")
		)

	# ✅ branch guard: assignee must cover log.school (self or descendant)
	log_school = sl.school
	assignee_anchor = (
		frappe.defaults.get_user_default("school", user)
		or frappe.db.get_value("Employee", {"user_id": user}, "school")
	)
	if not assignee_anchor:
		frappe.throw(
			_("Assignee has no School set (User Default or Employee.school)."),
			title=_("Missing School")
		)

	# single SQL: is log_school within assignee_anchor branch? (assignee_anchor ≤ log_school in lft/rgt)
	ok = frappe.db.sql(
		"""
		SELECT 1
		FROM `tabSchool` s1
		JOIN `tabSchool` s2
			ON s2.lft >= s1.lft AND s2.rgt <= s1.rgt
		WHERE s1.name = %s AND s2.name = %s
		""",
		(assignee_anchor, log_school),
	)

	# 🔒 enforce branch guard (required!)
	if not ok:
		frappe.throw(
			_("Assignee's school branch ({0}) does not include the log's school ({1}).")
			.format(assignee_anchor, log_school),
			title=_("Outside School Branch")
		)

	# ✅ role guard: assignee must have the expected role (from Next Step)
	required_role = sl.follow_up_role or "Academic Staff"
	if required_role and required_role not in set(frappe.get_roles(user)): 
		frappe.throw(
			_("Assignee must have the role: {0}.").format(required_role), 
			title=_("Role Mismatch")
		)

	# Permission: author, Academic Admin, or current assignee may (re)assign
	roles = set(frappe.get_roles())
	is_admin = "Academic Admin" in roles
	is_author = (frappe.session.user == sl.owner)
	current = frappe.db.get_value(
		"ToDo",
		{"reference_type": "Student Log", "reference_name": sl.name, "status": "Open"},
		"allocated_to"
	)
	allowed = is_admin or is_author or (current and current == frappe.session.user)
	if not allowed:
		frappe.throw(_("Not permitted to (re)assign this Student Log."))

	# Previous single open assignee (for clear "Old → New" message)
	prev_rows = frappe.get_all(
		"ToDo",
		filters={"reference_type": sl.doctype, "reference_name": sl.name, "status": "Open"},
		fields=["allocated_to"]
	)
	prev_user = prev_rows[0].allocated_to if len(prev_rows) == 1 else None

	# Clear existing opens (single-assignee policy)
	for r in prev_rows:
		try:
			if assign_remove:
				assign_remove(sl.doctype, sl.name, r.allocated_to)
			else:
				frappe.db.set_value(
					"ToDo",
					{"reference_type": sl.doctype, "reference_name": sl.name, "allocated_to": r.allocated_to, "status": "Open"},
					"status",
					"Closed"
				)
		except Exception:
			pass

	# Create new assignment (native API preferred)
	due_days = frappe.db.get_value("School", sl.school, "default_follow_up_due_in_days") or 5
	due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))

	if assign_add:
		assign_add({
			"doctype": sl.doctype,
			"name": sl.name,
			"assign_to": [user],
			"description": f"Follow up on Student Log for {sl.student_name}",
			"due_date": due_date
		})
	else:
		todo = frappe.new_doc("ToDo")
		todo.update({
			"allocated_to": user,
			"reference_type": sl.doctype,
			"reference_name": sl.name,
			"description": f"Follow up on Student Log for {sl.student_name}",
			"date": due_date,
			"status": "Open",
			"priority": "Medium",
		})
		todo.insert(ignore_permissions=True)

	# Mirror and recompute status (comment suppressed by reason="(re)assignment")
	sl.db_set("follow_up_person", user)
	sl._apply_status(sl._compute_follow_up_status(), reason="(re)assignment", write_immediately=True)

	# Timeline policy:
	# - With native assign_add: rely on Frappe's "Assigned to ..." for initial assign;
	#   only add a comment when it's a true reassignment Old → New.
	# - Without assign_add (fallback): emit a single concise comment ourselves.
	if assign_add:
		if prev_user and prev_user != user:
			sl.add_comment(
				"Info",
				_("Reassigned: {0} → {1}").format(sl._fullname(prev_user), sl._fullname(user))
			)
	else:
		# Fallback environment: add exactly one comment
		if prev_user and prev_user != user:
			msg = _("Reassigned: {0} → {1}").format(sl._fullname(prev_user), sl._fullname(user))
		else:
			msg = _("Assigned to {0}").format(sl._fullname(user))
		sl.add_comment("Info", msg)

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


@frappe.whitelist()
def complete_follow_up(follow_up_name: str):
	"""
	Mark a follow-up as completed and move the parent Student Log to 'Completed'.
	Permissions:
	- Follow-up author (owner), or
	- Academic Admin
	"""
	if not follow_up_name:
		frappe.throw(_("Missing follow-up name."))

	# Fetch only what we need from the follow-up
	fu_row = frappe.db.get_value(
		"Student Log Follow Up",
		follow_up_name,
		["name", "owner", "student_log"],
		as_dict=True
	)
	if not fu_row:
		frappe.throw(_("Follow-up not found: {0}").format(follow_up_name))
	if not fu_row.student_log:
		frappe.throw(_("This follow-up is not linked to a Student Log."))

	# Permission: follow-up author OR Academic Admin
	roles = set(frappe.get_roles())
	is_admin = "Academic Admin" in roles
	is_author = (frappe.session.user == fu_row.owner)
	if not (is_admin or is_author):
		frappe.throw(_("Only the follow-up author or an Academic Admin can complete this follow-up."))

	# Fetch minimal parent info
	log_row = frappe.db.get_value(
		"Student Log",
		fu_row.student_log,
		["name", "owner", "author_name", "student_name", "follow_up_status"],
		as_dict=True
	)
	if not log_row:
		frappe.throw(_("Parent Student Log not found."))

	# Idempotent: already Completed
	if (log_row.follow_up_status or "").lower() == "completed":
		return {"ok": True, "status": "Completed", "log": log_row.name}

	# 1) Set parent status → Completed (single column write)
	frappe.db.set_value("Student Log", log_row.name, "follow_up_status", "Completed")

	# 2) Close all OPEN ToDos on the parent in a single SQL
	frappe.db.sql(
		"""
		UPDATE `tabToDo`
		SET status = 'Closed'
		WHERE reference_type = %s AND reference_name = %s AND status = 'Open'
		""",
		("Student Log", log_row.name),
	)

	# 3) Timeline entry (direct Comment insert; avoids loading parent doc)
	try:
		link = frappe.utils.get_link_to_form("Student Log Follow Up", follow_up_name)
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Student Log",
			"reference_name": log_row.name,
			"content": _("Follow-up completed by {user} — see {link}").format(
				user=frappe.utils.get_fullname(frappe.session.user),
				link=link
			),
		}).insert(ignore_permissions=True)
	except Exception:
		pass

	# 4) Notify the log author (bell + realtime fallback)
	author_user = log_row.owner or None
	if not author_user and log_row.author_name:
		author_user = frappe.db.get_value(
			"Employee",
			{"employee_full_name": log_row.author_name},
			"user_id"
		)

	if author_user and author_user != frappe.session.user:
		# Bell notification
		try:
			frappe.get_doc({
				"doctype": "Notification Log",
				"subject": _("Follow-up completed"),
				"email_content": _("A follow-up for {0} has been completed. Click to review.")
					.format(log_row.student_name or log_row.name),
				"type": "Alert",
				"for_user": author_user,
				"from_user": frappe.session.user,
				"document_type": "Student Log",
				"document_name": log_row.name,
			}).insert(ignore_permissions=True)
		except Exception:
			# Realtime fallback
			try:
				frappe.publish_realtime(
					event="inbox_notification",
					message={
						"type": "Alert",
						"subject": _("Follow-up completed"),
						"message": _("A follow-up for {0} has been completed. Click to review.")
							.format(log_row.student_name or log_row.name),
						"reference_doctype": "Student Log",
						"reference_name": log_row.name
					},
					user=author_user
				)
			except Exception:
				pass

	return {"ok": True, "status": "Completed", "log": log_row.name}

@frappe.whitelist()
def complete_log(log_name: str):
	"""
	Mark the Student Log as 'Completed'.
	Permissions: only the log author (owner) can complete.
	Effects:
	- Set follow_up_status = 'Completed'
	- Close any OPEN ToDos referencing this log
	- Add concise timeline entry
	"""
	if not log_name:
		frappe.throw(_("Missing Student Log name."))

	# Fetch minimal fields
	log_row = frappe.db.get_value(
		"Student Log",
		log_name,
		["name", "owner", "student_name", "follow_up_status"],
		as_dict=True
	)
	if not log_row:
		frappe.throw(_("Student Log not found: {0}").format(log_name))

	# Permission: only author
	if frappe.session.user != log_row.owner:
		frappe.throw(_("Only the author of this Student Log can mark it as Completed."))

	# Idempotent: already Completed
	if (log_row.follow_up_status or "").lower() == "completed":
		return {"ok": True, "status": "Completed", "log": log_row.name}

	# 1) Update status (single column write)
	frappe.db.set_value("Student Log", log_row.name, "follow_up_status", "Completed")

	# 2) Close all OPEN ToDos for this log (single SQL)
	frappe.db.sql(
		"""
		UPDATE `tabToDo`
		SET status = 'Closed'
		WHERE reference_type = %s AND reference_name = %s AND status = 'Open'
		""",
		("Student Log", log_row.name),
	)

	# 3) Timeline entry (direct insert)
	try:
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Student Log",
			"reference_name": log_row.name,
			"content": _("Log marked <b>Completed</b> by {user}.").format(
				user=frappe.utils.get_fullname(frappe.session.user)
			),
		}).insert(ignore_permissions=True)
	except Exception:
		pass

	return {"ok": True, "status": "Completed", "log": log_row.name}
