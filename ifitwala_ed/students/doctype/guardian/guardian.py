# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# Copyright (c) 2024, François de Ryckel
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils.csvutils import getlink  # used in invite_guardian
from frappe.utils import get_link_to_form


class Guardian(Document):
	def onload(self):
		# Non-persistent helpers for the form
		load_address_and_contact(self)
		self.load_students()

	def before_insert(self):
		# Build a Contact up-front for this guardian
		self.contact_doc = self.get_or_create_contact()

	def validate(self):
		# Robust full name assembly
		self.guardian_full_name = " ".join(
			filter(None, [self.guardian_first_name, self.guardian_last_name])
		)

	def after_insert(self):
		self.update_links()

	# ------------------------------------------------------------------
	# Quick view: load linked students efficiently
	# ------------------------------------------------------------------
	def load_students(self):
		# Build the 'students' child table on load (not saved)
		self.set("students", [])
		rows = frappe.db.sql(
			"""
			SELECT
				sg.parent AS student,
				s.student_full_name AS student_name,
				s.student_gender AS student_gender
			FROM `tabStudent Guardian` sg
			INNER JOIN `tabStudent` s ON s.name = sg.parent
			WHERE sg.guardian = %s
			""",
			(self.name,),
			as_dict=True,
		)
		for r in rows:
			self.append("students", r)

	# ------------------------------------------------------------------
	# Contact creation (idempotent)
	# ------------------------------------------------------------------
	def get_or_create_contact(self):
		# Try to reuse by 'user' first, else create
		contact_name = None
		if getattr(self, "user", None):
			contact_name = frappe.db.get_value("Contact", {"user": self.user}, "name")
		if not contact_name and getattr(self, "guardian_email", None):
			# fall back by primary email if present
			contact_name = frappe.db.get_value(
				"Contact Email", {"email_id": self.guardian_email, "is_primary": 1}, "parent"
			)

		if contact_name:
			return frappe.get_doc("Contact", contact_name)

		contact = frappe.new_doc("Contact")
		contact.first_name = self.guardian_first_name
		contact.last_name = self.guardian_last_name
		if getattr(self, "salutation", None):
			contact.salutation = self.salutation
		if getattr(self, "user", None):
			contact.user = self.user
		if getattr(self, "guardian_gender", None):
			contact.gender = self.guardian_gender
		if getattr(self, "guardian_email", None):
			contact.append("email_ids", {"email_id": self.guardian_email, "is_primary": 1})
		if getattr(self, "guardian_mobile_phone", None):
			contact.mobile_no = self.guardian_mobile_phone
			contact.append("phone_nos", {"phone": self.guardian_mobile_phone, "is_primary": 1})

		contact.insert(ignore_permissions=True)
		return contact

	# ------------------------------------------------------------------
	# Ensure the Contact links back to this Guardian
	# ------------------------------------------------------------------
	def update_links(self):
		contact = getattr(self, "contact_doc", None)
		if not contact:
			# Try to find a contact if we somehow missed it
			contact_name = frappe.db.get_value("Contact", {"user": getattr(self, "user", None)}, "name")
			if not contact_name and getattr(self, "guardian_email", None):
				contact_name = frappe.db.get_value(
					"Contact Email", {"email_id": self.guardian_email, "is_primary": 1}, "parent"
				)
			if not contact_name:
				return
			contact = frappe.get_doc("Contact", contact_name)

		exists = frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": "Contact",
				"parentfield": "links",
				"parent": contact.name,
				"link_doctype": "Guardian",
				"link_name": self.name,
			},
		)
		if not exists:
			contact.append(
				"links",
				{"link_doctype": "Guardian", "link_name": self.name, "link_title": self.guardian_full_name},
			)
			contact.save(ignore_permissions=True)


# ----------------------------------------------------------------------
# Invite a Guardian to become a Website User
# ----------------------------------------------------------------------
@frappe.whitelist()
def invite_guardian(guardian):
	guardian_doc = frappe.get_doc("Guardian", guardian)

	if not guardian_doc.guardian_email:
		frappe.throw(_("Please add an email address and try again."))

	existing = frappe.db.get_value("User", {"email": guardian_doc.guardian_email}, "name")
	if existing:
		frappe.msgprint(
			_("The user {0} already exists.").format(get_link_to_form("User", existing))
		)
		return existing

	user = frappe.get_doc(
		{
			"doctype": "User",
			"first_name": guardian_doc.guardian_first_name,
			"last_name": guardian_doc.guardian_last_name,
			"email": guardian_doc.guardian_email,
			"mobile_no": guardian_doc.guardian_mobile_phone,
			"user_type": "Website User",
			"send_welcome_email": 1,
		}
	)
	user.flags.ignore_permissions = True
	user.insert()
	user.add_roles("Guardian")

	frappe.msgprint(
		_("User {0} created and welcomed with an email").format(getlink("User", user.name))
	)
	return user.name

def on_doctype_update():
	frappe.db.add_index("Guardian", "guardian_email")
