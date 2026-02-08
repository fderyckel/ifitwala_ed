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
	_force_redirect_response,
	STAFF_ROLES,
	RESTRICTED_ROLES,
	RESTRICTED_ROUTES,
)
from ifitwala_ed.api.users import redirect_user_to_entry_portal, _resolve_login_redirect_path


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


class TestAfterLoginRedirect(FrappeTestCase):
	"""Test after_login hook redirect functionality (Cyra Option A)."""

	def test_after_login_redirects_student_to_portal(self):
		"""Student should be redirected to /portal via after_login hook."""
		# Create test user with Student role
		user = frappe.new_doc("User")
		user.email = "test_student_after_login@example.com"
		user.first_name = "Test"
		user.last_name = "Student After Login"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		# Create Student record
		student = frappe.new_doc("Student")
		student.first_name = "Test"
		student.last_name = "Student After Login"
		student.student_email = user.email
		student.student_user_id = user.email
		student.save()

		try:
			# Simulate logged-in user
			frappe.set_user(user.email)
			
			# Clear any existing response
			frappe.local.response = {}
			
			# Call after_login hook
			redirect_user_to_entry_portal()
			
			# Verify redirect is set to /portal
			self.assertEqual(frappe.local.response.get("redirect_to"), "/portal")
			self.assertEqual(frappe.local.response.get("home_page"), "/portal")
			self.assertEqual(frappe.local.response.get("location"), "/portal")
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Student", student.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_after_login_does_not_redirect_staff(self):
		"""Staff should NOT be redirected by after_login - let Frappe handle to /app/{workspace}."""
		# Create test user with staff role
		user = frappe.new_doc("User")
		user.email = "test_staff_after_login@example.com"
		user.first_name = "Test"
		user.last_name = "Staff After Login"
		user.enabled = 1
		user.add_roles("Academic User")
		user.save()

		try:
			# Simulate logged-in user
			frappe.set_user(user.email)
			
			# Clear any existing response
			frappe.local.response = {}
			
			# Call after_login hook
			redirect_user_to_entry_portal()
			
			# Verify NO redirect is set for staff (let Frappe handle it)
			self.assertIsNone(frappe.local.response.get("redirect_to"))
			self.assertIsNone(frappe.local.response.get("home_page"))
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("User", user.email, force=True)

	def test_after_login_redirects_guardian_to_portal(self):
		"""Guardian should be redirected to /portal via after_login hook."""
		# Create test user with Guardian role
		user = frappe.new_doc("User")
		user.email = "test_guardian_after_login@example.com"
		user.first_name = "Test"
		user.last_name = "Guardian After Login"
		user.enabled = 1
		user.add_roles("Guardian")
		user.save()

		# Create Guardian record
		guardian = frappe.new_doc("Guardian")
		guardian.guardian_first_name = "Test"
		guardian.guardian_last_name = "Guardian After Login"
		guardian.guardian_email = user.email
		guardian.user = user.email
		guardian.save()

		try:
			# Simulate logged-in user
			frappe.set_user(user.email)
			
			# Clear any existing response
			frappe.local.response = {}
			
			# Call after_login hook
			redirect_user_to_entry_portal()
			
			# Verify redirect is set to /portal
			self.assertEqual(frappe.local.response.get("redirect_to"), "/portal")
			self.assertEqual(frappe.local.response.get("home_page"), "/portal")
			self.assertEqual(frappe.local.response.get("location"), "/portal")
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Guardian", guardian.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_after_login_redirects_admissions_to_admissions(self):
		"""Admissions Applicant should be redirected to /admissions via after_login hook."""
		# Create test user with Admissions Applicant role
		user = frappe.new_doc("User")
		user.email = "test_admissions_after_login@example.com"
		user.first_name = "Test"
		user.last_name = "Admissions After Login"
		user.enabled = 1
		user.add_roles("Admissions Applicant")
		user.save()

		# Create Student Applicant record
		applicant = frappe.new_doc("Student Applicant")
		applicant.first_name = "Test"
		applicant.last_name = "Admissions After Login"
		applicant.applicant_user = user.email
		applicant.save()

		try:
			# Simulate logged-in user
			frappe.set_user(user.email)
			
			# Clear any existing response
			frappe.local.response = {}
			
			# Call after_login hook
			redirect_user_to_entry_portal()
			
			# Verify redirect is set to /admissions
			self.assertEqual(frappe.local.response.get("redirect_to"), "/admissions")
			self.assertEqual(frappe.local.response.get("home_page"), "/admissions")
			self.assertEqual(frappe.local.response.get("location"), "/admissions")
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Student Applicant", applicant.name, force=True)
			frappe.delete_doc("User", user.email, force=True)

	def test_after_login_sets_home_page_in_user_doc(self):
		"""after_login hook should update User.home_page for persistence."""
		# Create test user with Student role
		user = frappe.new_doc("User")
		user.email = "test_home_page@example.com"
		user.first_name = "Test"
		user.last_name = "Home Page"
		user.enabled = 1
		user.add_roles("Student")
		user.save()

		# Create Student record
		student = frappe.new_doc("Student")
		student.first_name = "Test"
		student.last_name = "Home Page"
		student.student_email = user.email
		student.student_user_id = user.email
		student.save()

		try:
			# Simulate logged-in user
			frappe.set_user(user.email)
			
			# Clear any existing response
			frappe.local.response = {}
			
			# Call after_login hook
			redirect_user_to_entry_portal()
			
			# Verify User.home_page was updated
			user_doc = frappe.get_doc("User", user.email)
			self.assertEqual(user_doc.home_page, "/portal")
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc("Student", student.name, force=True)
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


class TestResolveLoginRedirectPath(FrappeTestCase):
	"""Test the _resolve_login_redirect_path helper function."""

	def test_admissions_applicant_returns_admissions(self):
		"""Admissions Applicant should return /admissions."""
		roles = {"Admissions Applicant"}
		path = _resolve_login_redirect_path(roles)
		self.assertEqual(path, "/admissions")

	def test_student_returns_portal(self):
		"""Student should return /portal (unified entry)."""
		roles = {"Student"}
		path = _resolve_login_redirect_path(roles)
		self.assertEqual(path, "/portal")

	def test_guardian_returns_portal(self):
		"""Guardian should return /portal (unified entry)."""
		roles = {"Guardian"}
		path = _resolve_login_redirect_path(roles)
		self.assertEqual(path, "/portal")

	def test_staff_returns_none(self):
		"""Staff should return None (let Frappe handle to /app/{workspace})."""
		roles = {"Academic User"}
		path = _resolve_login_redirect_path(roles)
		self.assertIsNone(path)

	def test_admissions_takes_priority(self):
		"""Admissions Applicant role should take priority over others."""
		roles = {"Admissions Applicant", "Student", "Academic User"}
		path = _resolve_login_redirect_path(roles)
		self.assertEqual(path, "/admissions")
