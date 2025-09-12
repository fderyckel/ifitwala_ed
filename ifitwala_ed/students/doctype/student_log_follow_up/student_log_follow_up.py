# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# resolve native assign API once (fallback closes ToDo directly)
try:
	from frappe.desk.form.assign_to import remove as assign_remove
except Exception:
	assign_remove = None


class StudentLogFollowUp(Document):
	def validate(self):
		# Guard: must point to a parent log
		if not self.student_log:
			frappe.throw(_("Please link a Student Log."))

		status = (frappe.db.get_value("Student Log", self.student_log, "follow_up_status") or "").lower()
		if status == "closed":
			frappe.throw(
				_("Parent Student Log is already <b>Closed</b>; follow-ups cannot be added or edited."),
				title=_("Parent Closed")
			)			

		# Soft warning if someone else is the current assignee on the parent log
		assignee = frappe.db.get_value(
			"ToDo",
			{"reference_type": "Student Log", "reference_name": self.student_log, "status": "Open"},
			"allocated_to"
		)
		if assignee and assignee != frappe.session.user and not self.name:
			link = frappe.utils.get_link_to_form("Student Log", self.student_log)
			frappe.msgprint(
				_("{user} is currently assigned to follow up this log: {link}")
				.format(user=frappe.utils.get_fullname(assignee), link=link),
				indicator="orange"
			)

		# Disallow follow-ups once the parent is Completed
		log = frappe.get_doc("Student Log", self.student_log)
		if log.follow_up_status == "Completed":
			frappe.throw(_("Cannot add follow-up: the Student Log is already marked as Completed."))

		# Ensure follow_up_author is set (read-only field in schema)
		if not self.follow_up_author:
			self.follow_up_author = frappe.utils.get_fullname(frappe.session.user)

	def on_update(self):
		# Mapping: parent status Open → In Progress when any follow-up is edited
		log = frappe.get_doc("Student Log", self.student_log)
		if log.follow_up_status == "Open":
			log.db_set("follow_up_status", "In Progress")

	def on_submit(self):
		log = frappe.get_doc("Student Log", self.student_log)

		# Submission ≠ completion → ensure parent is In Progress
		if (log.follow_up_status or "").lower() != "in progress":
			log.db_set("follow_up_status", "In Progress")

		# Optionally sync auto-close policy from Next Step onto the parent log
		if log.next_step:
			days = frappe.get_value("Student Log Next Step", log.next_step, "auto_close_after_days")
			if days is not None:
				try:
					log.db_set("auto_close_after_days", int(days))
				except Exception:
					pass

		# Notify the parent author (bell + toast)
		author_user = log.owner or None
		if not author_user and log.author_name:
			author_user = frappe.db.get_value("Employee", {"employee_full_name": log.author_name}, "user_id")

		if author_user and author_user != frappe.session.user:
			# Persistent bell notification via Notification Log
			try:
				frappe.get_doc({
					"doctype": "Notification Log",
					"subject": _("Follow-up ready to review"),
					"email_content": _("Follow-up for {0} has been submitted. Click to review.")
						.format(log.student_name or log.name),
					"type": "Alert",
					"for_user": author_user,
					"from_user": frappe.session.user,
					"document_type": "Student Log",
					"document_name": log.name,
				}).insert(ignore_permissions=True)
			except Exception:
				# Fallback: realtime inbox-style event
				try:
					frappe.publish_realtime(
						event="inbox_notification",
						message={
							"type": "Alert",
							"subject": _("Follow-up ready to review"),
							"message": _("Follow-up for {0} has been submitted. Click to review.")
								.format(log.student_name or log.name),
							"reference_doctype": "Student Log",
							"reference_name": log.name
						},
						user=author_user
					)
				except Exception:
					pass

			# Optional lightweight toast in active sessions
			frappe.publish_realtime(
				event="follow_up_ready_to_review",
				message={"log_name": log.name, "student_name": log.student_name},
				user=author_user
			)

		# Single concise timeline entry on the parent
		log.add_comment(
			comment_type="Info",
			text=_("Follow-up submitted by {author} — see {link}").format(
				author=self.follow_up_author or frappe.utils.get_fullname(frappe.session.user),
				link=frappe.utils.get_link_to_form(self.doctype, self.name),
			),
		)


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
