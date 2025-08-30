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

	def after_insert(self):
		# Timeline: record that a follow-up was started
		log = frappe.get_doc("Student Log", self.student_log)
		log.add_comment(
			comment_type="Comment",
			text=_("Follow-up created by {author} — see {link}").format(
				author=self.follow_up_author or frappe.utils.get_fullname(frappe.session.user),
				link=frappe.utils.get_link_to_form(self.doctype, self.name),
			),
		)

	def on_update(self):
		# Mapping: parent status Open → In Progress when any follow-up is edited
		log = frappe.get_doc("Student Log", self.student_log)
		if log.follow_up_status == "Open":
			log.db_set("follow_up_status", "In Progress")

	def on_submit(self):
		log = frappe.get_doc("Student Log", self.student_log)

		# 1) Close any open native assignments on the parent (single-assignee policy)
		open_assignees = frappe.get_all(
			"ToDo",
			filters={"reference_type": "Student Log", "reference_name": log.name, "status": "Open"},
			fields=["allocated_to"]
		)
		for row in open_assignees:
			u = row.allocated_to
			try:
				if assign_remove:
					assign_remove("Student Log", log.name, u)
				else:
					frappe.db.set_value(
						"ToDo",
						{"reference_type": "Student Log", "reference_name": log.name, "allocated_to": u, "status": "Open"},
						"status",
						"Closed"
					)
			except Exception:
				frappe.db.set_value(
					"ToDo",
					{"reference_type": "Student Log", "reference_name": log.name, "allocated_to": u, "status": "Open"},
					"status",
					"Closed"
				)

		# 2) Mark parent as Completed (align with finalize flow)
		log.db_set("follow_up_status", "Completed")

		# 3) Optionally sync auto-close policy from Next Step onto the parent log
		if log.next_step:
			days = frappe.get_value("Student Log Next Step", log.next_step, "auto_close_after_days")
			if days is not None:
				try:
					log.db_set("auto_close_after_days", int(days))
				except Exception:
					pass

		# 4) Notify the parent author (persistent bell + optional toast) and add one concise timeline entry
		# Prefer the actual owner; fall back to resolving via Employee name if needed
		author_user = log.owner
		if not author_user and log.author_name:
			author_user = frappe.db.get_value("Employee", {"employee_full_name": log.author_name}, "user_id")

		# 4a) Persistent in-app bell (Notification dropdown)
		if author_user and author_user != frappe.session.user:
			frappe.publish_realtime(
				event="inbox_notification",
				message={
					"type": "Alert",
					"subject": _("Follow-up ready to review"),
					"message": _("Follow-up for {0} has been submitted. Click to review.").format(log.student_name or log.name),
					"reference_doctype": "Student Log",
					"reference_name": log.name
				},
				user=author_user
			)

			# 4b) (Optional) lightweight toast in active sessions
			frappe.publish_realtime(
				event="follow_up_ready_to_review",
				message={"log_name": log.name, "student_name": log.student_name},
				user=author_user
			)

		# 4c) Single concise timeline entry
		log.add_comment(
			comment_type="Info",
			text=_("Follow-up submitted by {author} — see {link}").format(
				author=self.follow_up_author or frappe.utils.get_fullname(frappe.session.user),
				link=frappe.utils.get_link_to_form(self.doctype, self.name),
			),
		)
