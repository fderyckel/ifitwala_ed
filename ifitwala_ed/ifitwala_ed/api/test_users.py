# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/ifitwala_ed/api/test_users.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.users import redirect_user_to_entry_portal, STAFF_ROLES


class TestUserRedirect(FrappeTestCase):
	"""Test login redirect logic for different user types."""

	def test_guardian_redirects_to_portal(self):
		"""Guardians should be redirected to /portal/guardian on login."""
		# Create test user with Guardian role
		user = frappe.new_doc("User")
		user.email = "test_guardian_redirect@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create Guardian record linked to user
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		# Simulate login
		frappe.set_user(user.email)
		frappe.local.response = {}

		# Call redirect function
		redirect_user_to_entry_portal()

		# Assert redirect to /portal/guardian
		self.assertEqual(frappe.local.response.get("home_page"), "/portal/guardian")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/guardian")
		self.assertEqual(frappe.local.response.get("type"), "redirect")

		# Verify home_page was set on User
		user.reload()
		self.assertEqual(user.home_page, "/portal/guardian")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Guardian", guardian.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_guardian_respects_existing_home_page(self):
		"""Guardians with explicit home_page choice should not be overridden."""
		# Create test user with Guardian role and explicit home_page
		user = frappe.new_doc("User")
		user.email = "test_guardian_custom@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian Custom"
		user.home_page = "/app"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create Guardian record
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian Custom"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		# Simulate login
		frappe.set_user(user.email)
		frappe.local.response = {}

		# Call redirect function
		redirect_user_to_entry_portal()

		# Assert NO redirect was set (respects explicit /app choice)
		self.assertNotIn("home_page", frappe.local.response)

		# Verify home_page was NOT changed
		user.reload()
		self.assertEqual(user.home_page, "/app")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Guardian", guardian.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_guardian_with_staff_role_priority(self):
		"""Guardians with staff roles should NOT be redirected to guardian portal.
		
		Staff roles take priority over Guardian routing. A user who is both
		a guardian and has a staff role (e.g., Teacher) should not be
		redirected to /portal/guardian.
		"""
		# Create test user with both Guardian and Teacher roles
		user = frappe.new_doc("User")
		user.email = "test_guardian_teacher@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian Teacher"
		user.enabled = 1
		user.add_roles("Guardian", "Teacher")
		user.save()

		# Create Guardian record linked to user
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian Teacher"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		# Simulate login
		frappe.set_user(user.email)
		frappe.local.response = {}

		# Call redirect function
		redirect_user_to_entry_portal()

		# Assert NO guardian redirect was set (staff priority)
		self.assertNotIn("home_page", frappe.local.response)
		self.assertNotEqual(frappe.local.response.get("redirect_to"), "/portal/guardian")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Guardian", guardian.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_staff_roles_constant(self):
		"""Verify STAFF_ROLES contains expected roles."""
		expected_roles = {
			"Academic User",
			"System Manager",
			"Teacher",
			"Administrator",
			"Finance User",
			"HR User",
			"HR Manager",
		}
		self.assertEqual(STAFF_ROLES, expected_roles)
