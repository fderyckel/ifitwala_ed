# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_log_follow_up/student_log_follow_up.py

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

		# Single read: parent status (only 'completed' is terminal now)
		status = (frappe.db.get_value("Student Log", self.student_log, "follow_up_status") or "").lower()
		if status == "completed":
			frappe.throw(
				_("Cannot add or edit a follow-up because the Student Log is already <b>Completed</b>.")
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

		# -----------------------------------------------------------------
		# CLOSE OPEN ToDo(s) for this log (single-open ToDo policy)
		# - Once a follow-up is submitted, the assignee's ToDo is considered done.
		# - Review responsibility shifts to the author (Focus "review" item).
		# -----------------------------------------------------------------
		open_todos = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": "Student Log",
				"reference_name": log.name,
				"status": "Open",
			},
			fields=["name", "allocated_to"],
			limit_page_length=50,
		)

		for t in open_todos:
			allocated_to = t.get("allocated_to")
			if assign_remove and allocated_to:
				# Uses Frappe's assignment removal when available
				try:
					assign_remove("Student Log", log.name, allocated_to)
					continue
				except Exception:
					pass

			# Fallback: close the ToDo row directly
			if t.get("name"):
				frappe.db.set_value("ToDo", t["name"], "status", "Closed")

		# Resolve key users
		author_user = log.owner or None
		if not author_user and getattr(log, "author_name", None):
			author_user = frappe.db.get_value("Employee", {"employee_full_name": log.author_name}, "user_id")
		assignee_user = log.follow_up_person or None

		# Notify the parent author (bell + realtime), skip if it's me
		if author_user and author_user != frappe.session.user:
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

		# Notify current assignee (follow_up_person) too; skip if self or same as author
		if assignee_user and assignee_user not in {frappe.session.user, author_user}:
			try:
				frappe.get_doc({
					"doctype": "Notification Log",
					"subject": _("New follow-up on assigned log"),
					"email_content": _("A new follow-up was added for {0}. Click to review.")
						.format(log.student_name or log.name),
					"type": "Alert",
					"for_user": assignee_user,
					"from_user": frappe.session.user,
					"document_type": "Student Log",
					"document_name": log.name,
				}).insert(ignore_permissions=True)
			except Exception:
				try:
					frappe.publish_realtime(
						event="inbox_notification",
						message={
							"type": "Alert",
							"subject": _("New follow-up on assigned log"),
							"message": _("A new follow-up was added for {0}. Click to review.")
								.format(log.student_name or log.name),
							"reference_doctype": "Student Log",
							"reference_name": log.name
						},
						user=assignee_user
					)
				except Exception:
					pass

		# Single concise timeline entry on the parent (refactored wording)
		actor = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user
		log.add_comment(
			comment_type="Info",
			text=_("{actor} submitted a follow up — see {link}").format(
				actor=actor,
				link=frappe.utils.get_link_to_form(self.doctype, self.name),
			),
		)

		# ------------------------------------------------------------
		# Close assignee ToDo on follow-up submit
		# - Focus "action" items are driven by OPEN ToDos.
		# - Submitting a follow-up means the assignee has acted.
		# - Only close the OPEN ToDo if it belongs to the current user
		#   (prevents closing a ToDo after reassignment).
		# ------------------------------------------------------------
		try:
			todo_name, todo_user = frappe.db.get_value(
				"ToDo",
				{
					"reference_type": "Student Log",
					"reference_name": log.name,
					"status": "Open",
				},
				["name", "allocated_to"],
			) or (None, None)

			if todo_name and todo_user and todo_user == frappe.session.user:
				if assign_remove:
					assign_remove("Student Log", log.name, todo_user)
				else:
					frappe.db.set_value("ToDo", todo_name, "status", "Closed")
		except Exception:
			pass

