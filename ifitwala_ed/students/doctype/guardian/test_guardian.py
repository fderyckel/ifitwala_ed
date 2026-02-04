# Copyright (c) 2024, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestGuardian(FrappeTestCase):
	pass


class TestGuardianUserCreation(FrappeTestCase):
	"""Test guardian user creation and portal routing."""

	def test_create_guardian_user_sets_home_page(self):
		"""Creating a guardian user should set their home_page to /portal/guardian."""
		# Create a guardian without a user first
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian Portal"
		guardian.guardian_email = "test_guardian_portal@example.com"
		guardian.save()

		# Verify no user exists yet
		self.assertFalse(guardian.user)
		self.assertFalse(frappe.db.exists("User", guardian.guardian_email))

		# Create the user via the guardian method
		user_name = guardian.create_guardian_user()

		# Verify user was created
		self.assertTrue(frappe.db.exists("User", user_name))
		user = frappe.get_doc("User", user_name)

		# Verify Guardian role was assigned
		roles = [r.role for r in user.roles]
		self.assertIn("Guardian", roles)

		# MOST IMPORTANT: Verify home_page is set to /portal/guardian for automatic portal routing
		self.assertEqual(user.home_page, "/portal/guardian")

		# Verify guardian record was updated with user link
		guardian.reload()
		self.assertEqual(guardian.user, user_name)

		# Cleanup
		frappe.delete_doc("Guardian", guardian.name, force=True)
		frappe.delete_doc("User", user_name, force=True)

	def test_create_guardian_user_links_existing_user(self):
		"""If user already exists, it should be linked and home_page set."""
		# Create user first
		user = frappe.new_doc("User")
		user.email = "existing_guardian_user@example.com"
		user.first_name = "Existing"
		user.last_name = "Guardian"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create guardian pointing to same email
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Existing"
		guardian.guardian_last_name = "Guardian"
		guardian.guardian_email = user.email
		guardian.save()

		# Try to create user - should link existing
		result = guardian.create_guardian_user()

		# Should return existing user name
		self.assertEqual(result, user.email)

		# Guardian should be linked
		guardian.reload()
		self.assertEqual(guardian.user, user.email)

		# Cleanup
		frappe.delete_doc("Guardian", guardian.name, force=True)
		frappe.delete_doc("User", user.email, force=True)
