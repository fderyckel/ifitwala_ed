# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
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

	def on_update(self):
		log = frappe.get_doc("Student Log", self.student_log)

		# Set the linked student log follow up status to "In Progress" if still Open
		if log.follow_up_status == "Open":
			log.db_set("follow_up_status", "In Progress")
			log.add_comment(
				comment_type="Comment",
				text=_(
					"A follow-up was started by {author} — see {link}"
				).format(
					author=self.follow_up_author,
					link=frappe.utils.get_link_to_form("Student Log Follow Up", self.name)
				)
			)	


	def on_submit(self):
		log = frappe.get_doc("Student Log", self.student_log)

		log.db_set("follow_up_status", "Closed")

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

		# Add comment when the follow-up is formally submitted (possibly closed)
		log.add_comment(
			comment_type="Comment",
			text=_(
				"The follow-up by {author} was submitted — see {link}"
			).format(
				author=self.follow_up_author,
				link=frappe.utils.get_link_to_form("Student Log Follow Up", self.name)
			)
		)


