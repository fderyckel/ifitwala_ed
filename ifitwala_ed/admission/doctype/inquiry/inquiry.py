# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, cint
from ifitwala_ed.admission.admission_utils import notify_admission_manager, set_inquiry_deadlines, update_sla_status
from frappe.desk.form.assign_to import remove as remove_assignment

class Inquiry(Document):
	def before_insert(self):
		if not self.submitted_at:
			self.submitted_at = frappe.utils.now()

	def after_insert(self):
		if not self.workflow_state:
			self.workflow_state = "New Inquiry"
			self.db_set("workflow_state", "New Inquiry")
		notify_admission_manager(self)


	def before_save(self):
		# Only sets first_contact_due_on if missing; followup_due_on is set on (re)assignment.
		set_inquiry_deadlines(self)		
		update_sla_status(self)

	@frappe.whitelist()
	def create_contact_from_inquiry(self):
		if self.contact:
			frappe.msgprint(_("This Inquiry is already linked to Contact: {0}").format(self.contact))
			return

		# Check for existing email or phone match
		existing_contact = None
		if self.email:
			existing_contact = frappe.db.get_value("Contact Email", {
				"email_id": self.email,
				"is_primary": 1
			}, "parent")

		if not existing_contact and self.phone_number:
			existing_contact = frappe.db.get_value("Contact Phone", {
				"phone": self.phone_number,
				"is_primary_mobile_no": 1
			}, "parent")

		if existing_contact:
			self.contact = existing_contact
			self.db_set("contact", existing_contact)
		else:
			contact = frappe.new_doc("Contact")
			contact.first_name = self.first_name
			if self.last_name:
				contact.last_name = self.last_name
			if self.email:
				contact.append("email_ids", {
					"email_id": self.email,
					"is_primary": 1
				})
			if self.phone_number:
				contact.append("phone_nos", {
					"phone": self.phone_number,
					"is_primary_mobile_no": 1
				})
			contact.append("links", {
				"link_doctype": "Inquiry",
				"link_name": self.name
			})
			contact.insert(ignore_permissions=True)
			self.contact = contact.name
			self.db_set("contact", contact.name)

		# ✅ Add comment to Inquiry, not Contact
		self.add_comment("Comment", text=_("Linked to Contact <b>{0}</b> on {1}.").format(
			frappe.bold(self.contact),
			frappe.utils.nowdate()
		))

	@frappe.whitelist()
	def mark_contacted(self, complete_todo=False):
		prev_assignee = self.assigned_to

		self.add_comment(
			"Comment",
			text=_("Inquiry marked as <b>Contacted</b> by {0} on {1}.").format(
				frappe.bold(frappe.session.user), now_datetime()
			),
		)

		# Update fields
		if self.workflow_state != "Contacted":
			self.db_set("workflow_state", "Contacted", update_modified=False)
		if self.get("followup_due_on"):
			self.db_set("followup_due_on", None, update_modified=False)

		# Optionally clear assignment on the doc
		if cint(complete_todo) and prev_assignee:
			self.db_set("assigned_to", None, update_modified=False)

		# Recompute SLA and persist
		update_sla_status(self)
		self.db_set("sla_status", self.sla_status, update_modified=False)

		# Close only the correct ToDo
		if cint(complete_todo) and prev_assignee:
			try:
				# 1) Remove native assignment (typically sets ToDo -> Cancelled)
				remove_assignment(doctype=self.doctype, name=self.name, assign_to=prev_assignee)
				# 2) Normalize only the cancelled assignment ToDo(s) to Closed
				frappe.db.sql(
					"""
					UPDATE `tabToDo`
						SET status = 'Closed'
					WHERE reference_type = %s
						AND reference_name = %s
						AND allocated_to = %s
						AND status = 'Cancelled'
					""",
					(self.doctype, self.name, prev_assignee),
				)
			except Exception:
				# Fallback: close only the most recent open ToDo for this assignee+doc
				todo_name = frappe.db.get_value(
					"ToDo",
					{
						"reference_type": self.doctype,
						"reference_name": self.name,
						"allocated_to": prev_assignee,
						"status": "Open",
					},
					"name",
					order_by="creation desc",
				)
				if todo_name:
					frappe.db.set_value("ToDo", todo_name, "status", "Closed", update_modified=False)

		return {"ok": True}