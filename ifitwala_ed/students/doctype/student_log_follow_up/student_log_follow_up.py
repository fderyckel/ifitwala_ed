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

		# 1) Close native assignment on the parent log (single-assignee policy)
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
					# fallback: close ToDo directly
					frappe.db.set_value(
						"ToDo",
						{"reference_type": "Student Log", "reference_name": log.name, "allocated_to": u, "status": "Open"},
						"status",
						"Closed"
					)
			except Exception:
				# last resort: close any matching open ToDos
				frappe.db.set_value(
					"ToDo",
					{"reference_type": "Student Log", "reference_name": log.name, "allocated_to": u, "status": "Open"},
					"status",
					"Closed"
				)

		# 2) Update mapping: Follow-Up submit → parent 'Closed' (author may later set 'Completed')
		log.db_set("follow_up_status", "Closed")

		# 3) Notify parent author (toast) and timeline comment
		log_author_user_id = frappe.db.get_value("Employee", {"employee_full_name": log.author_name}, "user_id")
		if log_author_user_id and log_author_user_id != frappe.session.user:
			frappe.publish_realtime(
				event="follow_up_ready_to_review",
				message={"log_name": log.name, "student_name": log.student_name},
				user=log_author_user_id
			)

		log.add_comment(
			comment_type="Comment",
			text=_("Follow-up submitted by {author} — see {link}").format(
				author=self.follow_up_author or frappe.utils.get_fullname(frappe.session.user),
				link=frappe.utils.get_link_to_form(self.doctype, self.name),
			),
		)
