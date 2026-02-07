# ifitwala_ed/test_website_entry.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.www.website import get_context


class TestWebsiteEntryRouting(FrappeTestCase):
	def test_logout_path_redirects_to_web_logout(self):
		"""Requests to /logout should normalize to /?cmd=web_logout."""
		original_path = getattr(frappe.request, "path", None)
		original_form_dict = getattr(frappe, "form_dict", None)
		try:
			frappe.set_user("Guest")
			frappe.request.path = "/logout"
			frappe.form_dict = frappe._dict()
			with self.assertRaises(frappe.Redirect):
				get_context(frappe._dict())
			self.assertEqual(frappe.local.flags.redirect_location, "/?cmd=web_logout")
		finally:
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			if original_form_dict is not None:
				frappe.form_dict = original_form_dict

	def test_web_logout_cmd_redirects_to_login(self):
		"""After web logout command, user should land on /login."""
		original_path = getattr(frappe.request, "path", None)
		original_form_dict = getattr(frappe, "form_dict", None)
		try:
			frappe.set_user("Guest")
			frappe.request.path = "/"
			frappe.form_dict = frappe._dict({"cmd": "web_logout"})
			with self.assertRaises(frappe.Redirect):
				get_context(frappe._dict())
			self.assertEqual(frappe.local.flags.redirect_location, "/login")
		finally:
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			if original_form_dict is not None:
				frappe.form_dict = original_form_dict

	def test_guest_home_validation_error_falls_back_to_login(self):
		"""Guest home render failures should redirect to /login."""
		original_path = getattr(frappe.request, "path", None)
		original_form_dict = getattr(frappe, "form_dict", None)
		try:
			frappe.set_user("Guest")
			frappe.request.path = "/"
			frappe.form_dict = frappe._dict()
			with patch(
				"ifitwala_ed.www.website.build_render_context",
				side_effect=frappe.ValidationError("bad home props"),
			):
				with self.assertRaises(frappe.Redirect):
					get_context(frappe._dict())
			self.assertEqual(frappe.local.flags.redirect_location, "/login")
		finally:
			frappe.set_user("Administrator")
			if original_path:
				frappe.request.path = original_path
			if original_form_dict is not None:
				frappe.form_dict = original_form_dict
