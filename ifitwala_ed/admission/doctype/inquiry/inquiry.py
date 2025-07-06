# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
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

		# --- Auto-create or link Contact ---
		if not self.contact and self.email:
			# Try to find existing contact by email
			contact_name = frappe.db.get_value("Contact Email", {
				"email_id": self.email,
				"is_primary": 1
			}, "parent")

			if not contact_name:
				# Create new Contact
				contact = frappe.new_doc("Contact")
				contact.first_name = self.first_name
				contact.last_name = self.last_name
				contact.append("email_ids", {"email_id": self.email, "is_primary": 1})
				if self.phone_number:
					contact.append("phone_nos", {"phone": self.phone_number,"is_primary_mobile_no": 1})
				contact.append("links", {"link_doctype": "Inquiry", "link_name": self.name})
				contact.insert(ignore_permissions=True)

				self.db_set("contact", contact.name)
				contact.add_comment("Comment", text=f"Linked to Inquiry <b>{self.name}</b> on {frappe.utils.nowdate()}.")
			else:
				# Link to existing contact
				self.db_set("contact", contact_name)
				contact = frappe.get_doc("Contact", contact_name)
				self.db_set("contact_name", contact.get_title())

				if not any(link.link_doctype == "Inquiry" and link.link_name == self.name for link in contact.links):
					contact.append("links", {
						"link_doctype": "Inquiry",
						"link_name": self.name
					})
					contact.save(ignore_permissions=True)


	def before_save(self):
		set_inquiry_deadlines(self)		
		update_sla_status(self)


