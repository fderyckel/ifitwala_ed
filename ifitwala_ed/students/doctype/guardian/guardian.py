# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/guardian/guardian.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils.csvutils import getlink  # used in invite_guardian


class Guardian(Document):
	def validate(self):
		# 1) Keep validate pure: compute title only
		self.guardian_full_name = " ".join(filter(None, [self.guardian_first_name, self.guardian_last_name]))

	def before_insert(self):
		# 2) Do nothing (keep insert path fast and predictable)
		pass

	def after_insert(self):
		# 3) Create/reuse Contact once, then link Contact → Guardian (no contact.save here)
		contact_name = self._get_or_create_contact()
		self._ensure_contact_link(contact_name)

	def on_update(self):
		# 4) Idempotent self-heal: if link missing, add it
		contact_name = self._find_contact_name()
		if contact_name:
			self._ensure_contact_link(contact_name)

	def onload(self):
		# 5) Read-only helpers for form quick view
		load_address_and_contact(self)
		self._load_students_quick_view()

	# ---------------- internal helpers ----------------

	def _find_contact_name(self) -> str | None:
		# Prefer user match, then primary email match
		if getattr(self, "user", None):
			name = frappe.db.get_value("Contact", {"user": self.user}, "name")
			if name:
				return name
		if getattr(self, "guardian_email", None):
			return frappe.db.get_value("Contact Email", {"email_id": self.guardian_email, "is_primary": 1}, "parent")
		return None

	def _get_or_create_contact(self) -> str:
		name = self._find_contact_name()
		if name:
			return name

		# Minimal new Contact; insert only (no extra save)
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

		# Keep it boring: one insert, ignore perms, no further saves
		contact.insert(ignore_permissions=True)
		return contact.name

	def _ensure_contact_link(self, contact_name: str):
		# If link already exists, stop
		if frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": "Contact",
				"parentfield": "links",
				"parent": contact_name,
				"link_doctype": "Guardian",
				"link_name": self.name,
			},
		):
			return

		# Insert the child row directly — avoids Contact.on_update loops
		frappe.get_doc({
			"doctype": "Dynamic Link",
			"parenttype": "Contact",
			"parentfield": "links",
			"parent": contact_name,
			"link_doctype": "Guardian",
			"link_name": self.name,
			"link_title": self.guardian_full_name,
		}).insert(ignore_permissions=True)

	def _load_students_quick_view(self):
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


# ---------------- public API ----------------
@frappe.whitelist()
def invite_guardian(guardian: str):
	guardian_doc = frappe.get_doc("Guardian", guardian)

	if not guardian_doc.guardian_email:
		frappe.throw(_("Please add an email address and try again."))

	# If a user already exists, link it and return
	existing = frappe.db.get_value("User", {"email": guardian_doc.guardian_email}, "name")
	if existing:
		frappe.db.set_value("Guardian", guardian, "user", existing, update_modified=False)  # <-- no doc.save()
		frappe.msgprint(_("The user {0} already exists and has been linked to this guardian.")
			.format(get_link_to_form("User", existing)))
		return existing

	# Create a new Website User (mobile is optional for User)
	user = frappe.get_doc({
		"doctype": "User",
		"first_name": guardian_doc.guardian_first_name,
		"last_name": guardian_doc.guardian_last_name,
		"email": guardian_doc.guardian_email,
		"mobile_no": guardian_doc.guardian_mobile_phone or "",
		"user_type": "Website User",
		"send_welcome_email": 1,
	})
	user.flags.ignore_permissions = True
	user.insert()
	user.add_roles("Guardian")

	# Persist the link without saving the Guardian doc (avoids mandatory checks firing)
	frappe.db.set_value("Guardian", guardian, "user", user.name, update_modified=False)

	frappe.msgprint(_("User {0} created and welcomed with an email").format(getlink("User", user.name)))
	return user.name
