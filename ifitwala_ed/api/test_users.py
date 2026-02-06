# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/test_users.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.users import redirect_user_to_entry_portal, STAFF_ROLES


class TestUserRedirect(FrappeTestCase):
	"""Test unified login redirect logic."""

	def test_all_users_redirect_to_portal(self):
		"""Standard users should be redirected to /portal on login."""
		# Create test user
		user = frappe.new_doc("User")
		user.email = "test_user_portal@example.com"
		user.first_name = "Test"
		user.last_name = "User"
		user.enabled = 1
		user.save()

		# Simulate login
		frappe.set_user(user.email)
		frappe.local.response = {}

		# Call redirect function
		redirect_user_to_entry_portal()

		# Assert redirect to /portal
		self.assertEqual(frappe.local.response.get("home_page"), "/portal")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal")
		self.assertEqual(frappe.local.response.get("type"), "redirect")

		# Verify home_page was set on User
		user.reload()
		self.assertEqual(user.home_page, "/portal")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("User", user.email, force=True)

	def test_admissions_applicant_redirects_to_admissions(self):
		"""Admissions Applicants should be redirected to /admissions (not /portal)."""
		# Create test user with Admissions Applicant role
		user = frappe.new_doc("User")
		user.email = "test_admissions_applicant@example.com"
		user.first_name = "Test"
		user.last_name = "Admissions Applicant"
		user.enabled = 1
		user.add_roles("Admissions Applicant")
		user.save()

		# Create Student Applicant record linked to user
		applicant = frappe.new_doc("Student Applicant")
		applicant.first_name = "Test"
		applicant.last_name = "Applicant"
		applicant.applicant_user = user.email
		applicant.save()

		# Simulate login
		frappe.set_user(user.email)
		frappe.local.response = {}

		# Call redirect function
		redirect_user_to_entry_portal()

		# Assert redirect to /admissions (separate admissions portal)
		self.assertEqual(frappe.local.response.get("home_page"), "/admissions")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/admissions")
		self.assertEqual(frappe.local.response.get("type"), "redirect")

		# Verify home_page was set on User
		user.reload()
		self.assertEqual(user.home_page, "/admissions")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Student Applicant", applicant.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_guardian_redirects_to_portal(self):
		"""Guardians should be redirected to /portal (unified portal)."""
		# Create test user with Guardian role
		user = frappe.new_doc("User")
		user.email = "test_guardian_portal@example.com"
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

		# Assert redirect to unified /portal
		self.assertEqual(frappe.local.response.get("home_page"), "/portal")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Guardian", guardian.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_student_redirects_to_portal(self):
		"""Students should be redirected to /portal (not /sp)."""
		# Create test user with Student role
		user = frappe.new_doc("User")
		user.email = "test_student_portal@example.com"
		user.first_name = "Test"
		user.last_name = "Student"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		# Create Student record linked to user
		student = frappe.new_doc("Student")
		student.first_name = "Test"
		student.last_name = "Student"
		student.student_email = user.email
		student.student_user_id = user.email
		student.save()

		# Simulate login
		frappe.set_user(user.email)
		frappe.local.response = {}

		# Call redirect function
		redirect_user_to_entry_portal()

		# Assert redirect to unified /portal (not legacy /sp)
		self.assertEqual(frappe.local.response.get("home_page"), "/portal")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Student", student.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_staff_redirects_to_portal(self):
		"""Staff should be redirected to /portal (not /portal/staff)."""
		# Create test user with Employee role
		user = frappe.new_doc("User")
		user.email = "test_staff_portal@example.com"
		user.first_name = "Test"
		user.last_name = "Staff"
		user.enabled = 1
		user.add_roles("Employee")
		user.save()

		# Create Employee record linked to user
		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Staff"
		employee.user_id = user.email
		employee.employment_status = "Active"
		employee.save()

		# Simulate login
		frappe.set_user(user.email)
		frappe.local.response = {}

		# Call redirect function
		redirect_user_to_entry_portal()

		# Assert redirect to unified /portal (not /portal/staff)
		self.assertEqual(frappe.local.response.get("home_page"), "/portal")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Employee", employee.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_guest_user_ignored(self):
		"""Guest users should not trigger redirect."""
		frappe.set_user("Guest")
		frappe.local.response = {}

		# Call redirect function
		redirect_user_to_entry_portal()

		# Assert no redirect was set
		self.assertNotIn("home_page", frappe.local.response)
		self.assertNotIn("redirect_to", frappe.local.response)

		# Cleanup
		frappe.set_user("Administrator")

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
