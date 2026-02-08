# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/test_users.py

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

from ifitwala_ed.api.users import (
	_consume_post_login_portal_redirect,
	_post_login_redirect_cache_key,
	redirect_user_to_entry_portal,
)


class TestUserRedirect(FrappeTestCase):
	"""Test role-based login redirect logic."""

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

		# Verify home_page was set on User
		user.reload()
		self.assertEqual(user.home_page, "/admissions")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Student Applicant", applicant.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_guardian_redirects_to_portal(self):
		"""Guardians should be redirected to /portal/guardian."""
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

		# Assert redirect to explicit guardian portal
		self.assertEqual(frappe.local.response.get("home_page"), "/portal/guardian")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/guardian")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Guardian", guardian.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_student_redirects_to_portal(self):
		"""Students should be redirected to /portal/student."""
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

		# Assert redirect to explicit student portal (not legacy /sp)
		self.assertEqual(frappe.local.response.get("home_page"), "/portal/student")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/student")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Student", student.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_staff_redirects_to_portal(self):
		"""Staff should be redirected to /portal/staff."""
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

		# Assert redirect to explicit staff portal
		self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

		# Cleanup
		frappe.set_user("Administrator")
		frappe.delete_doc("Employee", employee.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_temporary_leave_employee_redirects_to_staff_portal(self):
		"""Temporary Leave employee should still be redirected to /portal/staff."""
		user = frappe.new_doc("User")
		user.email = "test_staff_temporary_leave_portal@example.com"
		user.first_name = "Test"
		user.last_name = "Staff Temp Leave"
		user.enabled = 1
		user.add_roles("Employee")
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Staff Temp Leave"
		employee.user_id = user.email
		employee.employment_status = "Temporary Leave"
		employee.save()

		frappe.set_user(user.email)
		frappe.local.response = {}
		redirect_user_to_entry_portal()

		self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

		frappe.set_user("Administrator")
		frappe.delete_doc("Employee", employee.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_active_employee_without_employee_role_redirects_to_staff(self):
		"""Active employee record should route to staff portal even without Employee role."""
		user = frappe.new_doc("User")
		user.email = "test_staff_portal_no_employee_role@example.com"
		user.first_name = "Test"
		user.last_name = "Staff No Role"
		user.enabled = 1
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Staff No Role"
		employee.user_id = user.email
		employee.employment_status = "Active"
		employee.save()

		frappe.set_user(user.email)
		frappe.local.response = {}
		redirect_user_to_entry_portal()

		self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

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

	def test_suspended_employee_redirects_to_web_logout(self):
		"""Suspended employee should be forced to web logout after login."""
		user = frappe.new_doc("User")
		user.email = "test_suspended_employee_redirect@example.com"
		user.first_name = "Test"
		user.last_name = "Suspended Employee"
		user.enabled = 1
		user.add_roles("Employee")
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Suspended Employee"
		employee.user_id = user.email
		employee.employment_status = "Suspended"
		employee.save()

		frappe.set_user(user.email)
		frappe.local.response = {}
		redirect_user_to_entry_portal()

		self.assertEqual(frappe.local.response.get("redirect_to"), "/?cmd=web_logout")

		frappe.set_user("Administrator")
		frappe.delete_doc("Employee", employee.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_relieving_date_cutoff_redirects_to_web_logout(self):
		"""Employee with reached relieving date should be forced to web logout."""
		user = frappe.new_doc("User")
		user.email = "test_relieving_date_cutoff_redirect@example.com"
		user.first_name = "Test"
		user.last_name = "Relieving Cutoff"
		user.enabled = 1
		user.add_roles("Employee")
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Relieving Cutoff"
		employee.user_id = user.email
		employee.employment_status = "Active"
		employee.relieving_date = frappe.utils.today()
		employee.save()

		frappe.set_user(user.email)
		frappe.local.response = {}
		redirect_user_to_entry_portal()

		self.assertEqual(frappe.local.response.get("redirect_to"), "/?cmd=web_logout")

		frappe.set_user("Administrator")
		frappe.delete_doc("Employee", employee.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_employee_guardian_precedence_redirects_to_staff(self):
		"""Multi-role users follow Staff > Student > Guardian priority."""
		user = frappe.new_doc("User")
		user.email = "test_employee_guardian_precedence@example.com"
		user.first_name = "Test"
		user.last_name = "Priority"
		user.enabled = 1
		user.add_roles("Employee")
		user.add_roles("Guardian")
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Priority"
		employee.user_id = user.email
		employee.employment_status = "Active"
		employee.save()

		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Priority"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		frappe.set_user(user.email)
		frappe.local.response = {}
		redirect_user_to_entry_portal()

		self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
		self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

		frappe.set_user("Administrator")
		frappe.delete_doc("Guardian", guardian.name, force=True)
		frappe.delete_doc("Employee", employee.name, force=True)
		frappe.delete_doc("User", user.email, force=True)

	def test_login_sets_one_time_post_login_redirect_marker(self):
		"""Login redirect should stage a one-time portal target for first-hop /app."""
		user = frappe.new_doc("User")
		user.email = "test_staff_login_marker@example.com"
		user.first_name = "Test"
		user.last_name = "Login Marker"
		user.enabled = 1
		user.add_roles("Employee")
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Login Marker"
		employee.user_id = user.email
		employee.employment_status = "Active"
		employee.save()

		session_id = "test-session-login-marker"
		cache_key = _post_login_redirect_cache_key(session_id)
		frappe.cache().delete_value(cache_key)

		frappe.set_user(user.email)
		frappe.local.response = {}

		try:
			with patch("ifitwala_ed.api.users._get_session_sid", return_value=session_id):
				redirect_user_to_entry_portal()
				self.assertEqual(
					frappe.cache().get_value(cache_key),
					"/portal/staff",
				)
				self.assertEqual(
					_consume_post_login_portal_redirect(),
					"/portal/staff",
				)
				self.assertIsNone(_consume_post_login_portal_redirect())
		finally:
			frappe.cache().delete_value(cache_key)
			frappe.set_user("Administrator")
			frappe.delete_doc("Employee", employee.name, force=True)
			frappe.delete_doc("User", user.email, force=True)
