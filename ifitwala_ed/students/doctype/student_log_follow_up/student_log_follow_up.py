# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StudentLogFollowUp(Document):

	def validate(self):
		if self.student_log and not self.name:
			# Only apply on creation (not updates)
			existing = frappe.get_all(
				"Student Log Follow Up",
				filters={
					"student_log": self.student_log,
					"status": ["not in", ["Closed", "Completed"]]
				},
				fields=["name", "assigned_to"],
				limit=1
			)

			if existing:
				existing_doc = existing[0]
				assigned_to = existing_doc.assigned_to
				if assigned_to != frappe.session.user:
					link = frappe.utils.get_link_to_form("Student Log Follow Up", existing_doc.name)
					frappe.msgprint(_("{user} has already started a {link} on this student log.").format(
						user=frappe.utils.get_fullname(assigned_to),
						link=link
					))

	def after_save(self):
		log = frappe.get_doc("Student Log", self.student_log)

		# Set the parent log to "In Progress" if still Open
		if log.follow_up_status == "Open":
			log.db_set("follow_up_status", "In Progress")

		# Notify original author only when this follow-up is Closed
		if self.status == "Closed":
			author_user = frappe.db.get_value("Employee", log.author, "user_id")
			if author_user and author_user != frappe.session.user:
				frappe.publish_realtime(
					event="follow_up_ready_to_review",
					message={
						"log_name": log.name,
						"student_name": log.student_name
					},
					user=author_user
				)
			# Add comment to Student Log when follow-up is first saved (i.e. started)
		if self.docstatus == 0:
			frappe.get_doc({
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "Student Log",
				"reference_name": self.student_log,
				"content": _(
					"A follow-up was started by {author} — see {link}"
				).format(
					author=self.author_name,
					link=frappe.utils.get_link_to_form("Student Log Follow Up", self.name)
				)
			}).insert(ignore_permissions=True)	


	def after_submit(self):
		log = frappe.get_doc("Student Log", self.student_log)

		if log.follow_up_status not in ("Closed",):
			log.db_set("follow_up_status", "Completed")

		# Get auto-close config from Next Step
		if log.next_step:
			auto_close_days = frappe.db.get_value("Student Log Next Step", log.next_step, "auto_close_after_days")
			if auto_close_days:
				log.db_set("auto_close_after_days", auto_close_days)

		# Add comment when the follow-up is formally submitted (possibly closed)
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Student Log",
			"reference_name": self.student_log,
			"content": _(
				"The follow-up by {author} was submitted — see {link}"
			).format(
				author=self.author_name,
				link=frappe.utils.get_link_to_form("Student Log Follow Up", self.name)
			)
		}).insert(ignore_permissions=True)


