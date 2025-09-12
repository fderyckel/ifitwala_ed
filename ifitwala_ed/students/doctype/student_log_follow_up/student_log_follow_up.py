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

