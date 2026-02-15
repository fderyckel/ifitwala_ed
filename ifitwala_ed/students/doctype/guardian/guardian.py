# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/guardian/guardian.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils import get_link_to_form
from ifitwala_ed.routing.policy import canonical_path_for_section, has_staff_portal_access


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
		
		# 4) If Guardian is created with a user already linked, ensure portal routing
		if getattr(self, "user", None):
			self._ensure_guardian_portal_routing(self.user)

	def on_update(self):
		# 4) Idempotent self-heal: if link missing, add it
		contact_name = self._find_contact_name()
		if contact_name:
			self._ensure_contact_link(contact_name)
		
		# 5) If user field was changed or newly set, ensure portal routing
		if self._has_user_changed():
			self._ensure_guardian_portal_routing(self.user)

	def onload(self):
		# 6) Read-only helpers for form quick view
		load_address_and_contact(self)
		self._load_students_quick_view()

	# ---------------- internal helpers ----------------

	def _has_user_changed(self) -> bool:
		"""Check if the user field was changed during this save."""
		if self.is_new():
			return bool(getattr(self, "user", None))
		
		previous = self.get_doc_before_save()
		if not previous:
			return bool(getattr(self, "user", None))
		
		old_user = getattr(previous, "user", None)
		new_user = getattr(self, "user", None)
		return old_user != new_user and new_user

	def _ensure_guardian_portal_routing(self, user_email: str):
		"""
		Ensure the linked user has Guardian role and correct home_page for portal routing.
		Called when Guardian is created or user field is updated.
		"""
		if not user_email or not frappe.db.exists("User", user_email):
			return
		
		user_roles = set(frappe.get_roles(user_email))
		
		# Don't override home_page for staff members - they get their own routing
		if has_staff_portal_access(user=user_email, roles=user_roles):
			return
		
		# Add Guardian role if missing
		if "Guardian" not in user_roles:
			try:
				user = frappe.get_doc("User", user_email)
				user.add_roles("Guardian")
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					f"Guardian portal routing role update failed for user {user_email}",
				)
		
		guardian_home = canonical_path_for_section("guardian")
		# Set home_page for portal routing if not already set to guardian portal
		current_home_page = frappe.db.get_value("User", user_email, "home_page")
		if current_home_page != guardian_home:
			try:
				frappe.db.set_value("User", user_email, "home_page", guardian_home, update_modified=False)
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					f"Guardian portal routing home_page update failed for user {user_email}",
				)

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

	def create_guardian_user(self):
		if not self.guardian_email:
			frappe.throw(_("Please add an email address first."))

		# If a User with this email already exists, link it and ensure proper portal setup
		if frappe.db.exists("User", self.guardian_email):
			if self.user != self.guardian_email:
				self.db_set("user", self.guardian_email, update_modified=False)
			
			# Ensure existing user has Guardian role and correct home_page for portal routing
			user = frappe.get_doc("User", self.guardian_email)
			roles = [r.role for r in user.roles]
			if "Guardian" not in roles:
				user.add_roles("Guardian")
			
			guardian_home = canonical_path_for_section("guardian")
			# Set home_page so guardian is routed to /guardian on login
			if user.home_page != guardian_home:
				frappe.db.set_value("User", user.name, "home_page", guardian_home, update_modified=False)
			
			frappe.msgprint(
				_("User {0} already exists and has been linked.")
				.format(get_link_to_form("User", self.guardian_email))
			)
			return self.guardian_email

		try:
			# Prepare a Contact and bind it to the future User (name is the email)
			contact_name = self._find_contact_name() or self._get_or_create_contact()
			if contact_name:
				# Bind contact to user *now* so core update_contact will update instead of creating a new Contact
				frappe.db.set_value("Contact", contact_name, "user", self.guardian_email, update_modified=False)

			user = frappe.get_doc({
				"doctype": "User",
				"enabled": 1,
				"first_name": self.guardian_first_name,
				"last_name": self.guardian_last_name,
				"email": self.guardian_email,
				"username": self.guardian_email,
				"mobile_no": self.guardian_mobile_phone or "",
				"user_type": "Website User",
				"send_welcome_email": 1,  # invite-style (flip to 0 if you prefer silent)
			})
			user.flags.ignore_permissions = True

			# Prevent Contact→Guardian sync loop during this controlled create
			frappe.flags.skip_contact_to_guardian_sync = True

			# Mirror your Student flow: add role then save
			user.add_roles("Guardian")
			user.save()

			guardian_home = canonical_path_for_section("guardian")
			# Set home_page so guardian is routed to /guardian on login
			frappe.db.set_value("User", user.name, "home_page", guardian_home, update_modified=False)

		except Exception as e:
			frappe.log_error(f"Error creating user for guardian {self.name}: {e}")
			frappe.throw(_("Error creating user for this guardian. Check Error Log."))
		finally:
			frappe.flags.skip_contact_to_guardian_sync = False

		# Persist the link without running Guardian.validate()
		self.db_set("user", user.name, update_modified=False)
		frappe.msgprint(_("User {0} has been created").format(get_link_to_form("User", user.name)))
		return user.name

# ---------------- public API ----------------
@frappe.whitelist()
def create_guardian_user(guardian: str):
	doc = frappe.get_doc("Guardian", guardian)
	return doc.create_guardian_user()
