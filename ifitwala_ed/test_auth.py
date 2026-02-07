# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/test_auth.py
# Tests for authentication hooks and access control

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.auth import before_request, STAFF_ROLES, RESTRICTED_ROLES, RESTRICTED_ROUTES


class TestAuthBeforeRequest(FrappeTestCase):
	"""Test before_request hook for portal user desk/app access protection."""

	def test_restricted_routes_defined(self):
		"""Verify restricted routes include /desk and /app."""
		self.assertIn("/desk", RESTRICTED_ROUTES)
		self.assertIn("/app", RESTRICTED_ROUTES)

	def test_restricted_roles_defined(self):
		"""Verify expected restricted roles are defined."""
		self.assertIn("Student", RESTRICTED_ROLES)
		self.assertIn("Guardian", RESTRICTED_ROLES)
		self.assertIn("Admissions Applicant", RESTRICTED_ROLES)

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
		"""Guardian without staff role accessing /desk should be redirected to /portal/guardian."""
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

	def test_student_accessing_desk_is_redirected(self):
		"""Student without staff role accessing /desk should be redirected to /portal/student."""
		# Create test user with Student role only
		user = frappe.new_doc("User")
		user.email = "test_student_desk@example.com"
		user.first_name = "Test"
		user.last_name = "Student"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		# Create Student record
		student = frappe.new_doc("Student")
		student.first_name = "Test"
		student.last_name = "Student"
		student.student_email = user.email
		student.student_user_id = user.email
		student.save()

		# Simulate request as student
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/desk"

		try:
			# Should raise Redirect
			with self.assertRaises(frappe.Redirect):
				before_request()
			
			# Verify redirect location
			self.assertEqual(frappe.local.flags.redirect_location, "/portal/student")
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Student", student.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_student_accessing_app_is_redirected(self):
		"""Student accessing /app should be redirected to /portal/student."""
		# Create test user with Student role
		user = frappe.new_doc("User")
		user.email = "test_student_app@example.com"
		user.first_name = "Test"
		user.last_name = "Student"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		# Create Student record
		student = frappe.new_doc("Student")
		student.first_name = "Test"
		student.last_name = "Student"
		student.student_email = user.email
		student.student_user_id = user.email
		student.save()

		# Simulate request as student
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/app"

		try:
			# Should raise Redirect
			with self.assertRaises(frappe.Redirect):
				before_request()
			
			# Verify redirect location
			self.assertEqual(frappe.local.flags.redirect_location, "/portal/student")
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Student", student.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_admissions_applicant_accessing_desk_is_redirected(self):
		"""Admissions Applicant accessing /desk should be redirected to /admissions."""
		# Create test user with Admissions Applicant role
		user = frappe.new_doc("User")
		user.email = "test_admissions_desk@example.com"
		user.first_name = "Test"
		user.last_name = "Admissions"
		user.enabled = 1
		user.add_roles("Admissions Applicant")
		user.save()

		# Create Student Applicant record
		applicant = frappe.new_doc("Student Applicant")
		applicant.first_name = "Test"
		applicant.last_name = "Applicant"
		applicant.applicant_user = user.email
		applicant.save()

		# Simulate request as admissions applicant
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/desk"

		try:
			# Should raise Redirect
			with self.assertRaises(frappe.Redirect):
				before_request()
			
			# Verify redirect to /admissions (not /portal)
			self.assertEqual(frappe.local.flags.redirect_location, "/admissions")
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Student Applicant", applicant.name, force=True)
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

	def test_guardian_with_active_employee_can_access_desk(self):
		"""Guardian with active Employee role should be allowed to access /desk."""
		user = frappe.new_doc("User")
		user.email = "test_guardian_employee_access@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian Employee"
		user.enabled = 1
		user.add_roles("Guardian", "Employee")
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Guardian Employee"
		employee.user_id = user.email
		employee.employment_status = "Active"
		employee.save()

		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian Employee"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		frappe.set_user(user.email)
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/desk"

		try:
			result = before_request()
			self.assertIsNone(result)
		finally:
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("Employee", employee.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_active_employee_root_app_redirects_to_portal_staff(self):
		"""Active Employee hitting /app without opt-in should be redirected to /portal/staff."""
		user = frappe.new_doc("User")
		user.email = "test_employee_root_app_redirect@example.com"
		user.first_name = "Test"
		user.last_name = "Employee Redirect"
		user.enabled = 1
		user.add_roles("Employee")
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Employee Redirect"
		employee.user_id = user.email
		employee.employment_status = "Active"
		employee.save()

		frappe.set_user(user.email)
		original_path = getattr(frappe.request, "path", None)
		original_form_dict = getattr(frappe.local, "form_dict", None)
		frappe.request.path = "/app"
		frappe.local.form_dict = frappe._dict()

		try:
			with self.assertRaises(frappe.Redirect):
				before_request()
			self.assertEqual(frappe.local.flags.redirect_location, "/portal/staff")
		finally:
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.local.form_dict = original_form_dict
			frappe.delete_doc("Employee", employee.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_active_employee_root_app_with_opt_in_can_access_desk(self):
		"""Active Employee hitting /app with portal_desk=1 should be allowed."""
		user = frappe.new_doc("User")
		user.email = "test_employee_root_app_optin@example.com"
		user.first_name = "Test"
		user.last_name = "Employee Optin"
		user.enabled = 1
		user.add_roles("Employee")
		user.save()

		employee = frappe.new_doc("Employee")
		employee.first_name = "Test"
		employee.last_name = "Employee Optin"
		employee.user_id = user.email
		employee.employment_status = "Active"
		employee.save()

		frappe.set_user(user.email)
		original_path = getattr(frappe.request, "path", None)
		original_form_dict = getattr(frappe.local, "form_dict", None)
		frappe.request.path = "/app"
		frappe.local.form_dict = frappe._dict({"portal_desk": "1"})

		try:
			result = before_request()
			self.assertIsNone(result)
		finally:
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.local.form_dict = original_form_dict
			frappe.delete_doc("Employee", employee.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_student_with_staff_role_can_access_desk(self):
		"""Student with staff role should be allowed to access /desk."""
		# Create test user with Student + Teacher roles
		user = frappe.new_doc("User")
		user.email = "test_student_staff@example.com"
		user.first_name = "Test"
		user.last_name = "Student Staff"
		user.enabled = 1
		user.add_roles("Student", "Teacher")
		user.save()

		# Create Student record
		student = frappe.new_doc("Student")
		student.first_name = "Test"
		student.last_name = "Student Staff"
		student.student_email = user.email
		student.student_user_id = user.email
		student.save()

		# Simulate request
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/desk"

		try:
			# Should NOT raise Redirect (staff takes priority)
			result = before_request()
			self.assertIsNone(result)
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Student", student.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_non_restricted_user_can_access_desk(self):
		"""Non-restricted user (Academic User) should be allowed to access /desk."""
		# Create test user without restricted roles
		user = frappe.new_doc("User")
		user.email = "test_norestrict@example.com"
		user.first_name = "Test"
		user.last_name = "No Restrict"
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

	def test_student_can_access_portal(self):
		"""Student should be allowed to access /portal routes."""
		# Create test user with Student role
		user = frappe.new_doc("User")
		user.email = "test_student_portal@example.com"
		user.first_name = "Test"
		user.last_name = "Student Portal"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		# Create Student record
		student = frappe.new_doc("Student")
		student.first_name = "Test"
		student.last_name = "Student Portal"
		student.student_email = user.email
		student.student_user_id = user.email
		student.save()

		# Simulate request as student
		frappe.set_user(user.email)
		
		# Mock request path
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/portal"

		try:
			# Should NOT raise Redirect
			result = before_request()
			self.assertIsNone(result)
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Student", student.name, force=True)
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
		frappe.request.path = "/portal"

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
