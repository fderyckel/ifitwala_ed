# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/test_auth.py
# Tests for authentication hooks and access control

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.auth import (
	before_request,
	on_login,
	_resolve_portal_path,
	_get_first_login_flag_key,
	STAFF_ROLES,
	RESTRICTED_ROLES,
	RESTRICTED_ROUTES,
)


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
		"""Guardian without staff role accessing /desk should be redirected to /portal."""
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
			# Should set redirect response
			before_request()
			
			# Verify redirect location
			self.assertEqual(frappe.local.response.get("location"), "/portal")
			self.assertEqual(frappe.local.response.get("http_status_code"), 302)
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_student_accessing_desk_is_redirected(self):
		"""Student without staff role accessing /desk should be redirected to /portal."""
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
			# Should set redirect response
			before_request()
			
			# Verify redirect location
			self.assertEqual(frappe.local.response.get("location"), "/portal")
			self.assertEqual(frappe.local.response.get("http_status_code"), 302)
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Student", student.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_student_accessing_app_is_redirected(self):
		"""Student accessing /app should be redirected to /portal."""
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
			# Should set redirect response
			before_request()
			
			# Verify redirect location
			self.assertEqual(frappe.local.response.get("location"), "/portal")
			self.assertEqual(frappe.local.response.get("http_status_code"), 302)
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
			# Should set redirect response
			before_request()
			
			# Verify redirect to /admissions (not /portal)
			self.assertEqual(frappe.local.response.get("location"), "/admissions")
			self.assertEqual(frappe.local.response.get("http_status_code"), 302)
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
			# Should NOT set redirect response (staff takes priority)
			result = before_request()
			# If we get here without exception, the test passes
			self.assertIsNone(result)
			self.assertIsNone(frappe.local.response.get("location"))
		finally:
			# Cleanup
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			frappe.delete_doc("Guardian", guardian.name, force=True)
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
			# Should NOT set redirect response (staff takes priority)
			result = before_request()
			self.assertIsNone(result)
			self.assertIsNone(frappe.local.response.get("location"))
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
			# Should NOT set redirect response
			result = before_request()
			self.assertIsNone(result)
			self.assertIsNone(frappe.local.response.get("location"))
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
			# Should NOT set redirect response
			result = before_request()
			self.assertIsNone(result)
			self.assertIsNone(frappe.local.response.get("location"))
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
			# Should NOT set redirect response
			result = before_request()
			self.assertIsNone(result)
			self.assertIsNone(frappe.local.response.get("location"))
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
			# Should NOT set redirect response for Guest
			result = before_request()
			self.assertIsNone(result)
			self.assertIsNone(frappe.local.response.get("location"))
		finally:
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path


class TestLoginRedirectGuard(FrappeTestCase):
	"""Test one-time post-login redirect guard functionality."""

	def test_on_login_sets_cache_flag(self):
		"""on_login hook should set the first-login cache flag."""
		# Create test user
		user = frappe.new_doc("User")
		user.email = "test_login_guard@example.com"
		user.first_name = "Test"
		user.last_name = "Login Guard"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		try:
			# Clear any existing flag
			cache_key = _get_first_login_flag_key(user.email)
			frappe.cache().delete(cache_key)

			# Simulate login
			frappe.set_user(user.email)
			on_login()

			# Verify flag is set in cache
			self.assertTrue(frappe.cache().get(cache_key))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User", user.email, force=True)

	def test_first_login_guard_redirects_staff_to_portal(self):
		"""Employee first request to /app should redirect to unified /portal."""
		# Create test user with staff role
		user = frappe.new_doc("User")
		user.email = "test_staff_guard@example.com"
		user.first_name = "Test"
		user.last_name = "Staff Guard"
		user.enabled = 1
		user.add_roles("Academic User")
		user.save()

		try:
			# Set up cache with first-login flag
			frappe.set_user(user.email)
			cache_key = _get_first_login_flag_key(user.email)
			frappe.cache().set(cache_key, True, expires_in=300)

			# Mock request to /app
			original_path = getattr(frappe.request, "path", None)
			frappe.request.path = "/app"

			try:
				# Should set redirect response
				before_request()

				# Verify redirect response is set
				self.assertEqual(frappe.local.response.get("location"), "/portal")
				self.assertEqual(frappe.local.response.get("http_status_code"), 302)
			finally:
				if original_path:
					frappe.request.path = original_path
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User", user.email, force=True)

	def test_first_login_guard_redirects_student_to_portal(self):
		"""Student first request to /app should redirect to unified /portal."""
		# Create test user with Student role
		user = frappe.new_doc("User")
		user.email = "test_student_guard@example.com"
		user.first_name = "Test"
		user.last_name = "Student Guard"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		# Create Student record
		student = frappe.new_doc("Student")
		student.first_name = "Test"
		student.last_name = "Student Guard"
		student.student_email = user.email
		student.student_user_id = user.email
		student.save()

		try:
			# Set up cache with first-login flag
			frappe.set_user(user.email)
			cache_key = _get_first_login_flag_key(user.email)
			frappe.cache().set(cache_key, True, expires_in=300)

			# Mock request to /app
			original_path = getattr(frappe.request, "path", None)
			frappe.request.path = "/app"

			try:
				# Should set redirect response
				before_request()

				# Verify redirect response is set
				self.assertEqual(frappe.local.response.get("location"), "/portal")
				self.assertEqual(frappe.local.response.get("http_status_code"), 302)
			finally:
				if original_path:
					frappe.request.path = original_path
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Student", student.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_first_login_guard_redirects_guardian_to_portal(self):
		"""Guardian first request to /app should redirect to unified /portal."""
		# Create test user with Guardian role
		user = frappe.new_doc("User")
		user.email = "test_guardian_guard@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian Guard"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create Guardian record
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian Guard"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		try:
			# Set up cache with first-login flag
			frappe.set_user(user.email)
			cache_key = _get_first_login_flag_key(user.email)
			frappe.cache().set(cache_key, True, expires_in=300)

			# Mock request to /app
			original_path = getattr(frappe.request, "path", None)
			frappe.request.path = "/app"

			try:
				# Should set redirect response
				before_request()

				# Verify redirect response is set
				self.assertEqual(frappe.local.response.get("location"), "/portal")
				self.assertEqual(frappe.local.response.get("http_status_code"), 302)
			finally:
				if original_path:
					frappe.request.path = original_path
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_first_login_guard_clears_flag_after_redirect(self):
		"""First-login flag should be cleared after guard processes."""
		# Create test user
		user = frappe.new_doc("User")
		user.email = "test_flag_clear@example.com"
		user.first_name = "Test"
		user.last_name = "Flag Clear"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		try:
			# Set up cache with first-login flag
			frappe.set_user(user.email)
			cache_key = _get_first_login_flag_key(user.email)
			frappe.cache().set(cache_key, True, expires_in=300)

			# Mock request to /app
			original_path = getattr(frappe.request, "path", None)
			frappe.request.path = "/app"

			# Should set redirect response
			before_request()

			# Verify flag is cleared from cache
			self.assertIsNone(frappe.cache().get(cache_key))

			if original_path:
				frappe.request.path = original_path
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User", user.email, force=True)

	def test_second_request_allows_staff_to_access_app(self):
		"""After first hop, staff should be able to access /app normally."""
		# Create test user with staff role
		user = frappe.new_doc("User")
		user.email = "test_staff_second@example.com"
		user.first_name = "Test"
		user.last_name = "Staff Second"
		user.enabled = 1
		user.add_roles("Academic User")
		user.save()

		try:
			# Simulate: first request (with flag) goes to portal
			frappe.set_user(user.email)
			cache_key = _get_first_login_flag_key(user.email)
			frappe.cache().set(cache_key, True, expires_in=300)

			original_path = getattr(frappe.request, "path", None)
			frappe.request.path = "/app"

			# First request should redirect
			before_request()
			self.assertEqual(frappe.local.response.get("location"), "/portal")

			# Clear response for next request simulation
			frappe.local.response = {}

			# Now simulate second request (flag cleared) - staff should access /app
			frappe.request.path = "/app/workspace/academics"

			# Should NOT set redirect response (staff can access desk after first hop)
			before_request()
			self.assertIsNone(frappe.local.response.get("location"))

			if original_path:
				frappe.request.path = original_path
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User", user.email, force=True)

	def test_guardian_never_lands_on_app_after_login(self):
		"""Guardian should never reach /app on first request after login."""
		# Create test user
		user = frappe.new_doc("User")
		user.email = "test_guardian_never_app@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian Never App"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create Guardian record
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian Never App"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		try:
			# Set up cache with first-login flag
			frappe.set_user(user.email)
			cache_key = _get_first_login_flag_key(user.email)
			frappe.cache().set(cache_key, True, expires_in=300)

			original_path = getattr(frappe.request, "path", None)
			frappe.request.path = "/app"

			# Should set redirect response
			before_request()

			# Verify redirect is NOT to /app
			redirect_location = frappe.local.response.get("location")
			self.assertNotEqual(redirect_location, "/app")
			self.assertTrue(redirect_location.startswith("/portal"))

			if original_path:
				frappe.request.path = original_path
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("User", user.email, force=True)


class TestResolvePortalPath(FrappeTestCase):
	"""Test the _resolve_portal_path helper function (Option B: unified /portal)."""

	def test_admissions_applicant_priority(self):
		"""Admissions Applicant should go to /admissions (separate portal)."""
		roles = {"Admissions Applicant", "Student", "Academic User"}
		path = _resolve_portal_path(roles)
		self.assertEqual(path, "/admissions")

	def test_staff_unified_portal_entry(self):
		"""Staff should use unified /portal entry (Option B architecture)."""
		roles = {"Student", "Academic User"}
		path = _resolve_portal_path(roles)
		self.assertEqual(path, "/portal")

	def test_student_unified_portal_entry(self):
		"""Student should use unified /portal entry (Option B architecture)."""
		roles = {"Guardian", "Student"}
		path = _resolve_portal_path(roles)
		self.assertEqual(path, "/portal")

	def test_guardian_unified_portal_entry(self):
		"""Guardian should use unified /portal entry (Option B architecture)."""
		roles = {"Guardian"}
		path = _resolve_portal_path(roles)
		self.assertEqual(path, "/portal")

	def test_unknown_roles_unified_portal_entry(self):
		"""Unknown roles should use unified /portal entry (Option B architecture)."""
		roles = {"Some Custom Role"}
		path = _resolve_portal_path(roles)
		self.assertEqual(path, "/portal")
