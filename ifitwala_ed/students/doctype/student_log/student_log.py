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
		Derive status from current DB state under the new semantics:
		- None            → follow-up not required or no clear state
		- "Open"          → exactly one open ToDo exists and no follow-ups yet
		- "In Progress"   → at least one follow-up exists (draft or submitted)
		- "Completed"     → preserved only if explicitly set (author/admin action)
		Notes:
		- Submitting a follow-up does NOT auto-complete the log anymore.
		"""
		# If follow-up isn't required or the doc isn't saved yet, no derived status
		if not frappe.utils.cint(self.requires_follow_up) or not self.name:
			return None

		# Preserve explicit terminal state
		if (self.follow_up_status or "").lower() == "completed":
			return "Completed"

		# Any follow-up (draft or submitted) means work is/was happening → In Progress
		if frappe.db.exists("Student Log Follow Up", {"student_log": self.name}):
			return "In Progress"

		# Otherwise, if exactly one open ToDo exists, we're Open
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
		- When requires_follow_up = 0 (pre-submit), mark status Completed quietly.
		- Derive status (timeline comments suppressed for auto reasons).
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
			# Derive from current DB state
			derived = self._compute_follow_up_status()

		else:
			# Follow-up not required
			self._unassign()
			self.follow_up_person = None
			self.next_step = None

			# Draft-only: immediately mark Completed (quietly)
			if self.docstatus == 0:
				self.follow_up_status = "Completed"
				derived = "Completed"
			else:
				# Submitted docs are immutable for this switch; keep current
				derived = self.follow_up_status

		# Apply derived status (suppresses timeline via reason)
		self._apply_status(derived, reason="recomputed on validate", write_immediately=False)

		# Infer school from program if missing
		if not self.school and self.program:
			self.school = frappe.db.get_value("Program", self.program, "school")

		self._assert_followup_transition_and_immutability()

	def on_submit(self):
		"""
		Submission invariants for the Student Log itself:
		- If requires_follow_up = 0, force status to 'Completed' and skip follow-up checks.
		- If requires_follow_up = 1, exactly one open assignment must exist.
		- Mirror that assignee into follow_up_person.
		- Recompute status; timeline comment is suppressed via _apply_status() reason.
		"""
		if not cint(self.requires_follow_up):
			# Directly mark as Completed on submit (idempotent, quiet)
			if (self.follow_up_status or "").lower() != "completed":
				self.db_set("follow_up_status", "Completed")
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
		"""Enforce legal status transitions and lock core fields once Completed."""
		old = self.get_doc_before_save() or frappe._dict()

		old_status = (old.get("follow_up_status") or "").lower()
		new_status = (self.follow_up_status or "").lower()

		# Allowed transitions (Completed is terminal)
		allowed = {
			None: {"", "open", "in progress"},
			"": {"open", "in progress"},
			"open": {"open", "in progress", "completed"},
			"in progress": {"in progress", "completed"},
			"completed": {"completed"},
		}

		# Normalize key for None/empty
		old_key = old_status if old_status else None
		if old_key not in allowed or new_status not in allowed[old_key]:
			# Permit no-change; otherwise block
			if new_status != old_status:
				frappe.throw(
					_("Illegal follow-up status change: {0} → {1}")
					.format(old_status or "None", new_status or "None"),
					title=_("Invalid Transition")
				)

		# Once Completed, lock core follow-up fields
		if (old_status == "completed") or (new_status == "completed" and old_status != "completed"):
			locked_fields = {
				"requires_follow_up",
				"next_step",
				"follow_up_role",
				"follow_up_person",
				"program",       # optional: protect context
				"academic_year", # optional: protect context
			}
			for f in locked_fields:
				if old.get(f) != self.get(f):
					frappe.throw(
						_("Field {0} cannot be changed after the log is Completed.").format(f),
						title=_("Locked After Completion")
					)

	# ---------------------------------------------------------------------
	# Assignment helpers
	# ---------------------------------------------------------------------
	def _assign_to(self, user):
		if not user:
			return

		# Was there already an OPEN assignee before we assign?
		had_open = frappe.db.exists(
			"ToDo",
			{
				"reference_type": self.doctype,
				"reference_name": self.name,
				"status": "Open",
			},
		)

		# due date from School.default_follow_up_due_in_days (fallback 5)
		due_days = 5
		if self.program:
			school = frappe.get_value("Program", self.program, "school")
			if school:
				due_days = frappe.get_value("School", school, "default_follow_up_due_in_days") or 5
		due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))

		# Create/ensure a single OPEN ToDo for the assignee
		desc = f"Follow up on the Student Log for {self.student_name}"
		if assign_add:
			assign_add({
				"doctype": self.doctype,
				"name": self.name,
				"assign_to": [user],
				"description": desc,
				"due_date": due_date
			})
		else:
			todo = frappe.new_doc("ToDo")
			todo.update({
				"owner": user,
				"allocated_to": user,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"description": desc,
				"date": due_date,
				"status": "Open",
				"priority": "Medium",
			})
			todo.insert(ignore_permissions=True)

		# Emit ONE clean "initial assignment" timeline note (not on reassign)
		if not had_open:
			try:
				actor  = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user
				target = frappe.utils.get_fullname(user) or user
				content = _("{} assigned {}: Follow up on the Student Log for {}").format(
					actor, target, self.student_name or self.name
				)
				frappe.get_doc({
					"doctype": "Comment",
					"comment_type": "Info",
					"reference_doctype": self.doctype,
					"reference_name": self.name,
					"content": content,
				}).insert(ignore_permissions=True)
			except Exception:
				pass


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
	"""
	Efficient (re)assignment:
	- Blocks when log is 'Completed'
	- Branch guard: assignee must be within school subtree
	- Role guard (target): assignee must have follow_up_role (fallback 'Academic Staff')
	- Perms (actor): Academic Admin OR log author OR current assignee OR user with follow_up_role
	- Bulk-closes existing OPEN ToDos; inserts one new ToDo
	- Mirrors follow_up_person; recomputes status via DB (no full doc loads)
	"""
	if not (log_name and user):
		frappe.throw(_("Missing parameters."))

	# Minimal parent fetch
	sl = frappe.db.get_value(
		"Student Log",
		log_name,
		["name", "owner", "school", "student_name", "follow_up_status", "follow_up_role"],
		as_dict=True,
	)
	if not sl:
		frappe.throw(_("Student Log not found: {0}").format(log_name))

	# Completed logs cannot be (re)assigned
	if (sl.follow_up_status or "").lower() == "completed":
		frappe.throw(
			_("This Student Log is already <b>Completed</b> and cannot be (re)assigned."),
			title=_("Follow-Up Completed")
		)

	# Branch guard: assignee must cover log.school (user default school or Employee.school)
	assignee_anchor = (
		frappe.defaults.get_user_default("school", user)
		or frappe.db.get_value("Employee", {"user_id": user}, "school")
	)
	if not assignee_anchor:
		frappe.throw(
			_("Assignee has no School set (User Default or Employee.school)."),
			title=_("Missing School")
		)

	ok = frappe.db.sql(
		"""
		SELECT 1
		FROM `tabSchool` s1
		JOIN `tabSchool` s2
			ON s2.lft >= s1.lft AND s2.rgt <= s1.rgt
		WHERE s1.name = %s AND s2.name = %s
		LIMIT 1
		""",
		(assignee_anchor, sl.school),
	)
	if not ok:
		frappe.throw(
			_("Assignee's school branch ({0}) does not include the log's school ({1}).")
			.format(assignee_anchor, sl.school),
			title=_("Outside School Branch")
		)

	# Role guard (target): assignee must have required role (fallback 'Academic Staff')
	required_role = sl.follow_up_role or "Academic Staff"
	if required_role and required_role not in set(frappe.get_roles(user)):
		frappe.throw(
			_("Assignee must have the role: {0}.").format(required_role),
			title=_("Role Mismatch")
		)

	# Permission (actor): author OR Academic Admin OR current assignee OR user with the associated role
	roles_current = set(frappe.get_roles())
	is_admin = "Academic Admin" in roles_current
	is_author = (frappe.session.user == sl.owner)
	current_assignee = frappe.db.get_value(
		"ToDo",
		{"reference_type": "Student Log", "reference_name": sl.name, "status": "Open"},
		"allocated_to",
	)
	is_current_assignee = bool(current_assignee and current_assignee == frappe.session.user)
	has_associated_role = required_role in roles_current

	allowed = is_admin or is_author or is_current_assignee or has_associated_role
	if not allowed:
		frappe.throw(_("Not permitted to (re)assign this Student Log."))

	# Keep previous single open assignee (for timeline message); then bulk-close all opens
	prev_user = current_assignee
	frappe.db.sql(
		"""
		UPDATE `tabToDo`
		SET status = 'Closed'
		WHERE reference_type = 'Student Log'
		  AND reference_name = %s
		  AND status = 'Open'
		""",
		(sl.name,),
	)

	# Create new OPEN ToDo for assignee (lean insert)
	due_days = frappe.db.get_value("School", sl.school, "default_follow_up_due_in_days") or 5
	due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))
	frappe.get_doc({
		"doctype": "ToDo",
		"allocated_to": user,
		"reference_type": "Student Log",
		"reference_name": sl.name,
		"description": f"Follow up on Student Log for {sl.student_name or sl.name}",
		"date": due_date,
		"status": "Open",
		"priority": "Medium",
	}).insert(ignore_permissions=True)

	# Mirror assignee on the parent
	frappe.db.set_value("Student Log", sl.name, "follow_up_person", user)

	# Recompute status cheaply:
	# any follow-up rows → In Progress; else with open ToDo → Open
	has_followups = bool(frappe.db.exists("Student Log Follow Up", {"student_log": sl.name}))
	new_status = "In Progress" if has_followups else "Open"
	if (sl.follow_up_status or "") != new_status:
		frappe.db.set_value("Student Log", sl.name, "follow_up_status", new_status)

	# Timeline note only for true reassignment Old → New
	if prev_user and prev_user != user:
		try:
			prev_full = frappe.utils.get_fullname(prev_user) or prev_user
			new_full = frappe.utils.get_fullname(user) or user
			frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Student Log",
				"reference_name": sl.name,
				"content": _("Reassigned: {0} → {1}").format(prev_full, new_full),
			}).insert(ignore_permissions=True)
		except Exception:
			pass

	return {"ok": True, "assigned_to": user, "status": new_status}


# ---------- scheduler: Completed → Closed ----------
def auto_close_completed_logs():
	"""
	Daily job: move 'In Progress' → 'Completed' after N days of inactivity.
	- Only affects logs where follow_up_status = 'In Progress'
	- Does NOT touch 'Open' logs
	- Closes any OPEN ToDos referencing those logs
	- Adds a concise audit comment per log
	Returns: number of logs completed.
	"""
	today = frappe.utils.today()

	rows = frappe.get_all(
		"Student Log",
		filters={"follow_up_status": "In Progress", "auto_close_after_days": [">", 0]},
		fields=["name", "modified", "auto_close_after_days"]
	)

	if not rows:
		return 0

	eligible = []
	threshold_by_log = {}
	for r in rows:
		last_updated = get_datetime(r.modified)
		if date_diff(today, last_updated.date()) >= r.auto_close_after_days:
			eligible.append(r.name)
			threshold_by_log[r.name] = r.auto_close_after_days

	if not eligible:
		return 0

	# 1) Close any OPEN ToDos for these logs in a single SQL
	frappe.db.sql(
		f"""
		UPDATE `tabToDo`
		SET status = 'Closed'
		WHERE reference_type = 'Student Log'
		  AND status = 'Open'
		  AND reference_name IN ({", ".join(["%s"] * len(eligible))})
		""",
		tuple(eligible),
	)

	# 2) Update status → Completed (use set_value per row to update 'modified' properly)
	for name in eligible:
		frappe.db.set_value("Student Log", name, "follow_up_status", "Completed")

	# 3) Add one concise audit comment per log (idempotent)
	for name in eligible:
		msg = f"Auto-completed after {threshold_by_log.get(name, 0)} days of inactivity."
		already = frappe.db.exists(
			"Comment",
			{
				"reference_doctype": "Student Log",
				"reference_name": name,
				"comment_type": "Info",
				"content": ("like", "Auto-completed after%"),
			},
		)
		if already:
			continue
		try:
			frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Student Log",
				"reference_name": name,
				"content": msg,
			}).insert(ignore_permissions=True)
		except Exception:
			pass

	return len(eligible)

@frappe.whitelist()
def complete_follow_up(follow_up_name: str):
	"""
	Close the parent Student Log (set follow_up_status = 'Completed') from a follow-up.
	Permissions:
	- Parent Student Log author (owner), OR
	- Academic Admin

	Note: any Academic Staff may create follow-ups, but only the log author or an Academic Admin
	can close the log via this action.
	"""
	if not follow_up_name:
		frappe.throw(_("Missing follow-up name."))

	# Fetch only what we need from the follow-up
	fu_row = frappe.db.get_value(
		"Student Log Follow Up",
		follow_up_name,
		["name", "student_log"],
		as_dict=True
	)
	if not fu_row:
		frappe.throw(_("Follow-up not found: {0}").format(follow_up_name))
	if not fu_row.student_log:
		frappe.throw(_("This follow-up is not linked to a Student Log."))

	# Fetch minimal parent info (including owner)
	log_row = frappe.db.get_value(
		"Student Log",
		fu_row.student_log,
		["name", "owner", "author_name", "student_name", "follow_up_status"],
		as_dict=True
	)
	if not log_row:
		frappe.throw(_("Parent Student Log not found."))

	# ---- Permission check (CHANGED) ----
	roles = set(frappe.get_roles())
	is_admin = "Academic Admin" in roles
	is_parent_author = (frappe.session.user == (log_row.owner or ""))

	if not (is_admin or is_parent_author):
		frappe.throw(_("Only the Student Log author or an Academic Admin can complete this log."))

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

	# 4) Notify the log author (bell + realtime fallback) — only if someone else completed it
	author_user = log_row.owner or None
	if author_user and author_user != frappe.session.user:
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

@frappe.whitelist()
def reopen_log(log_name: str):
	"""
	Reopen a 'Completed' Student Log → 'In Progress'.
	Permissions: Academic Admin OR log author (owner).
	Effects:
	- Set follow_up_status = 'In Progress'
	- If follow_up_person is set and no OPEN ToDo exists, create one with a sane due date
	- Add concise timeline entry
	- Notify follow_up_person (bell + realtime) if present
	"""
	if not log_name:
		frappe.throw(_("Missing Student Log name."))

	# Minimal fetch
	row = frappe.db.get_value(
		"Student Log",
		log_name,
		["name", "owner", "school", "student_name", "follow_up_status", "follow_up_person"],
		as_dict=True
	)
	if not row:
		frappe.throw(_("Student Log not found: {0}").format(log_name))

	# Only from Completed
	if (row.follow_up_status or "").lower() != "completed":
		frappe.throw(_("Only logs in <b>Completed</b> status can be reopened."))

	# Permission: author or Academic Admin
	roles = set(frappe.get_roles())
	is_admin = "Academic Admin" in roles
	is_author = (frappe.session.user == row.owner)
	if not (is_admin or is_author):
		frappe.throw(_("Only the log author or an Academic Admin can reopen this log."))

	# 1) Flip status → In Progress (single write)
	frappe.db.set_value("Student Log", row.name, "follow_up_status", "In Progress")

	# 2) Ensure an OPEN ToDo exists for current follow_up_person (if set)
	if row.follow_up_person:
		has_open = frappe.db.get_value(
			"ToDo",
			{"reference_type": "Student Log", "reference_name": row.name, "allocated_to": row.follow_up_person, "status": "Open"},
			"name"
		)
		if not has_open:
			due_days = frappe.db.get_value("School", row.school, "default_follow_up_due_in_days") or 5
			due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))
			frappe.get_doc({
				"doctype": "ToDo",
				"allocated_to": row.follow_up_person,
				"reference_type": "Student Log",
				"reference_name": row.name,
				"description": f"Follow up on Student Log for {row.student_name or row.name}",
				"date": due_date,
				"status": "Open",
				"priority": "Medium",
			}).insert(ignore_permissions=True)

	# 3) Timeline: concise audit note
	try:
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Student Log",
			"reference_name": row.name,
			"content": _("Log <b>reopened</b> by {user}.").format(
				user=frappe.utils.get_fullname(frappe.session.user)
			),
		}).insert(ignore_permissions=True)
	except Exception:
		pass

	# 4) Notify the follow_up_person (if any)
	if row.follow_up_person and row.follow_up_person != frappe.session.user:
		try:
			# Bell notification
			frappe.get_doc({
				"doctype": "Notification Log",
				"subject": _("Log reopened"),
				"email_content": _("A Student Log you’re assigned to was reopened. Click to review."),
				"type": "Alert",
				"for_user": row.follow_up_person,
				"from_user": frappe.session.user,
				"document_type": "Student Log",
				"document_name": row.name,
			}).insert(ignore_permissions=True)
		except Exception:
			# Realtime fallback
			try:
				frappe.publish_realtime(
					event="inbox_notification",
					message={
						"type": "Alert",
						"subject": _("Log reopened"),
						"message": _("A Student Log you’re assigned to was reopened. Click to review."),
						"reference_doctype": "Student Log",
						"reference_name": row.name
					},
					user=row.follow_up_person
				)
			except Exception:
				pass

	return {"ok": True, "status": "In Progress", "log": row.name}


