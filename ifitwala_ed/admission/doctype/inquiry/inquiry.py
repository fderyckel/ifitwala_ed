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
			existing = frappe.db.get_value("Dynamic Link", {
				"link_doctype": "Contact",
				"link_name": self.email
			}, "parent")

			if not existing:
				# No existing contact — create new
				contact = frappe.new_doc("Contact")
				contact.first_name = self.first_name
				contact.last_name = self.last_name
				contact.email_ids = [{"email_id": self.email, "is_primary": 1}]
				contact.links = [{"link_doctype": "Inquiry", "link_name": self.name}]
				contact.insert(ignore_permissions=True)
				self.db_set("contact", contact.name)
				self.db_set("contact_name", contact.get_title())
				contact.add_comment("Comment", text=f"Linked to Inquiry <b>{self.name}</b> on {frappe.utils.nowdate()}.")
			else:
				# Link to existing contact
				self.db_set("contact", existing)
				existing_contact = frappe.get_doc("Contact", existing)
				self.db_set("contact_name", existing_contact.get_title())
				# Optionally also link Inquiry → Contact
				existing_contact.append("links", {
					"link_doctype": "Inquiry",
					"link_name": self.name
				})
				existing_contact.save(ignore_permissions=True)		

	def before_save(self):
		set_inquiry_deadlines(self)		
		update_sla_status(self)


