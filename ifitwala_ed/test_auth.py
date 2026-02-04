# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/test_auth.py
# Tests for authentication hooks and access control

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.auth import before_request, STAFF_ROLES, GUARDIAN_RESTRICTED_ROUTES


class TestAuthBeforeRequest(FrappeTestCase):
	"""Test before_request hook for guardian desk/app access protection."""

	def test_guardian_restricted_routes_defined(self):
		"""Verify restricted routes include /desk and /app."""
		self.assertIn("/desk", GUARDIAN_RESTRICTED_ROUTES)
		self.assertIn("/app", GUARDIAN_RESTRICTED_ROUTES)

	def test_staff_roles_defined(self):
		"""Verify expected staff roles are defined."""
		expected = {
			"Academic User",
			"System Manager",
			"Teacher",
			"Administrator",
			"Finance User",
			"HR User",
			"HR Manager",
		}
		self.assertEqual(STAFF_ROLES, expected)

	def test_guardian_accessing_desk_is_redirected(self):
		"""Guardian without staff role accessing /desk should be redirected."""
		# Create test user with Guardian role only
		user = frappe.new_doc("User")
		user.email = "test_guardian_desk@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create Guardian record
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		# Simulate request as guardian
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/desk"

		try:
			# Should raise Redirect
			with self.assertRaises(frappe.Redirect):
				before_request()
			
			# Verify redirect location
			self.assertEqual(frappe.local.flags.redirect_location, "/portal/guardian")
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_guardian_accessing_app_is_redirected(self):
		"""Guardian without staff role accessing /app should be redirected."""
		# Create test user with Guardian role only
		user = frappe.new_doc("User")
		user.email = "test_guardian_app@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian App"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create Guardian record
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian App"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		# Simulate request as guardian
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/app"

		try:
			# Should raise Redirect
			with self.assertRaises(frappe.Redirect):
				before_request()
			
			# Verify redirect location
			self.assertEqual(frappe.local.flags.redirect_location, "/portal/guardian")
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_guardian_with_staff_role_can_access_desk(self):
		"""Guardian with staff role should be allowed to access /desk."""
		# Create test user with Guardian + Teacher roles
		user = frappe.new_doc("User")
		user.email = "test_guardian_staff@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian Staff"
		user.enabled = 1
		user.add_roles("Guardian", "Teacher")
		user.save()

		# Create Guardian record
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian Staff"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		# Simulate request as guardian with staff role
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/desk"

		try:
			# Should NOT raise Redirect (staff takes priority)
			result = before_request()
			# If we get here without exception, the test passes
			self.assertIsNone(result)
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_non_guardian_can_access_desk(self):
		"""Non-guardian user should be allowed to access /desk."""
		# Create test user without Guardian role
		user = frappe.new_doc("User")
		user.email = "test_nonguardian@example.com"
		user.first_name = "Test"
		user.last_name = "Non Guardian"
		user.enabled = 1
		user.add_roles("Academic User")
		user.save()

		# Simulate request
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/desk"

		try:
			# Should NOT raise Redirect
			result = before_request()
			self.assertIsNone(result)
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("User", user.email, force=True)

	def test_guardian_can_access_portal(self):
		"""Guardian should be allowed to access /portal routes."""
		# Create test user with Guardian role
		user = frappe.new_doc("User")
		user.email = "test_guardian_portal@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian Portal"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create Guardian record
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian Portal"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		# Simulate request as guardian
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/portal/guardian"

		try:
			# Should NOT raise Redirect
			result = before_request()
			self.assertIsNone(result)
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_guest_user_ignored(self):
		"""Guest users should be ignored by before_request."""
		frappe.set_user("Guest")
		
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/desk"

		try:
			# Should NOT raise Redirect for Guest
			result = before_request()
			self.assertIsNone(result)
		finally:
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
