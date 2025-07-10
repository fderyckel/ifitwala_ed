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


	def before_save(self):
		set_inquiry_deadlines(self)		
		update_sla_status(self)

	@frappe.whitelist()
	def create_contact(self):
		if self.contact:
			frappe.throw(_("A contact is already linked to this inquiry."))

		# Check if email already exists
		if self.email:
			existing_email = frappe.db.get_value("Contact Email", {
				"email_id": self.email,
				"is_primary": 1
			}, "parent")
			if existing_email:
				frappe.throw(_("A Contact with email <b>{0}</b> already exists: <a href='/app/contact/{1}'>{1}</a>").format(
					self.email, existing_email
				), title=_("Duplicate Email"))

		# Check if phone number already exists
		if self.phone_number:
			existing_phone = frappe.db.get_value("Contact Phone", {
				"phone": self.phone_number,
				"is_primary_mobile_no": 1
			}, "parent")
			if existing_phone:
				frappe.throw(_("A Contact with phone number <b>{0}</b> already exists: <a href='/app/contact/{1}'>{1}</a>").format(
					self.phone_number, existing_phone
				), title=_("Duplicate Phone"))

		# Create new contact
		contact = frappe.new_doc("Contact")
		contact.first_name = self.first_name
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
		contact.insert()

		self.db_set("contact", contact.name)

		contact.add_comment("Comment", text=f"Created from Inquiry <b>{self.name}</b>.")
		return contact.name

	


