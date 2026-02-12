# ifitwala_ed/test_admissions_route.py

from urllib.parse import quote

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.www.admissions.index import get_context


class TestAdmissionsRoute(FrappeTestCase):
	def test_guest_redirects_to_login(self):
		frappe.set_user("Guest")
		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/admissions"

		try:
			with self.assertRaises(frappe.Redirect):
				get_context(frappe._dict())

			self.assertEqual(
				frappe.local.flags.redirect_location,
				"/login?redirect-to=/admissions",
			)
		finally:
			frappe.set_user("Administrator")
			if original_path is not None:
				frappe.request.path = original_path

	def test_authenticated_non_admissions_user_is_logged_out_before_login_redirect(self):
		user = frappe.new_doc("User")
		user.email = "test_admissions_route_non_role@example.com"
		user.first_name = "No"
		user.last_name = "AdmissionsRole"
		user.enabled = 1
		user.save()

		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/admissions"
		frappe.set_user(user.email)

		try:
			with self.assertRaises(frappe.Redirect):
				get_context(frappe._dict())

			expected_login = "/login?redirect-to=/admissions"
			self.assertEqual(
				frappe.local.flags.redirect_location,
				f"/logout?redirect-to={quote(expected_login, safe='')}",
			)
		finally:
			frappe.set_user("Administrator")
			if original_path is not None:
				frappe.request.path = original_path
			frappe.delete_doc("User", user.email, force=True)

	def test_admissions_user_without_linked_applicant_is_logged_out_before_login_redirect(self):
		user = frappe.new_doc("User")
		user.email = "test_admissions_route_missing_applicant@example.com"
		user.first_name = "Missing"
		user.last_name = "Applicant"
		user.enabled = 1
		user.add_roles("Admissions Applicant")
		user.save()

		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/admissions"
		frappe.set_user(user.email)

		try:
			with self.assertRaises(frappe.Redirect):
				get_context(frappe._dict())

			expected_login = "/login?redirect-to=/admissions"
			self.assertEqual(
				frappe.local.flags.redirect_location,
				f"/logout?redirect-to={quote(expected_login, safe='')}",
			)
		finally:
			frappe.set_user("Administrator")
			if original_path is not None:
				frappe.request.path = original_path
			frappe.delete_doc("User", user.email, force=True)

	def test_linked_admissions_user_loads_admissions_context(self):
		user = frappe.new_doc("User")
		user.email = "test_admissions_route_linked@example.com"
		user.first_name = "Linked"
		user.last_name = "Applicant"
		user.enabled = 1
		user.add_roles("Admissions Applicant")
		user.save()

		applicant = frappe.new_doc("Student Applicant")
		applicant.first_name = "Linked"
		applicant.last_name = "Applicant"
		applicant.applicant_user = user.email
		applicant.save()

		original_path = getattr(frappe.request, "path", None)
		frappe.request.path = "/admissions"
		frappe.set_user(user.email)

		try:
			context = frappe._dict()
			result = get_context(context)
			self.assertEqual(result.applicant, applicant.name)
			self.assertEqual(result.title, "Admissions Portal")
		finally:
			frappe.set_user("Administrator")
			if original_path is not None:
				frappe.request.path = original_path
			frappe.delete_doc("Student Applicant", applicant.name, force=True)
			frappe.delete_doc("User", user.email, force=True)
