# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime
from ifitwala_ed.admission.admission_utils import notify_admission_manager, set_inquiry_deadlines, update_sla_status


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
		message = _("Inquiry marked as <b>Contacted</b> by {0} on {1}.").format(
			frappe.bold(frappe.session.user), now_datetime())
		self.add_comment("Comment", text=message)

		if frappe.parse_bool(complete_todo):
			todos = frappe.get_all("ToDo", filters={
				"reference_type": self.doctype,
				"reference_name": self.name,
				"status": "Open",
			})
			for todo in todos:
				todo_doc = frappe.get_doc("ToDo", todo.name)
				todo_doc.status = "Closed"
				todo_doc.save(ignore_permissions=True)

		# Set workflow_state to Contacted if not already set
		if self.workflow_state != "Contacted": 
			self.workflow_state = "Contacted" 
			
		# If assigned user is marking as contacted, set SLA as completed 
		if frappe.session.user == self.assigned_to: 
			self.sla_status = "✅ Completed" 

		self.save(ignore_permissions=True)
