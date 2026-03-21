# ifitwala_ed/website/tests/test_logout_route.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.www.logout import _safe_redirect_target, get_context


class TestLogoutRoute(FrappeTestCase):
    def test_safe_redirect_target_allows_internal_absolute_paths(self):
        self.assertEqual(_safe_redirect_target("/"), "/")
        self.assertEqual(_safe_redirect_target("/login?redirect-to=/admissions"), "/login?redirect-to=/admissions")

    def test_safe_redirect_target_blocks_external_or_relative_values(self):
        self.assertEqual(_safe_redirect_target("https://example.com"), "/")
        self.assertEqual(_safe_redirect_target("//example.com"), "/")
        self.assertEqual(_safe_redirect_target("login"), "/")

    def test_guest_logout_without_login_manager_redirects_without_error_log(self):
        original_login_manager = getattr(frappe.local, "login_manager", None)
        original_form_dict = getattr(frappe, "form_dict", None)
        original_redirect_location = getattr(frappe.local.flags, "redirect_location", None)

        try:
            frappe.set_user("Guest")
            if hasattr(frappe.local, "login_manager"):
                del frappe.local.login_manager
            frappe.form_dict = frappe._dict({"redirect_to": "/login?redirect-to=/admissions"})
            frappe.local.flags.redirect_location = None

            with patch("frappe.log_error") as mocked_log_error:
                with self.assertRaises(frappe.Redirect):
                    get_context(frappe._dict())

            self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=/admissions")
            mocked_log_error.assert_not_called()
        finally:
            if original_login_manager is None:
                if hasattr(frappe.local, "login_manager"):
                    del frappe.local.login_manager
            else:
                frappe.local.login_manager = original_login_manager

            if original_form_dict is None:
                if hasattr(frappe, "form_dict"):
                    delattr(frappe, "form_dict")
            else:
                frappe.form_dict = original_form_dict

            frappe.local.flags.redirect_location = original_redirect_location
            frappe.set_user("Administrator")

    def test_logout_route_calls_login_manager_logout_before_redirect(self):
        class _LoginManager:
            def __init__(self):
                self.called = False

            def logout(self):
                self.called = True

        original_login_manager = getattr(frappe.local, "login_manager", None)
        original_form_dict = getattr(frappe, "form_dict", None)
        original_redirect_location = getattr(frappe.local.flags, "redirect_location", None)
        login_manager = _LoginManager()

        try:
            frappe.set_user("Administrator")
            frappe.local.login_manager = login_manager
            frappe.form_dict = frappe._dict({"redirect_to": "/"})
            frappe.local.flags.redirect_location = None

            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())

            self.assertTrue(login_manager.called)
            self.assertEqual(frappe.local.flags.redirect_location, "/")
        finally:
            if original_login_manager is None:
                if hasattr(frappe.local, "login_manager"):
                    del frappe.local.login_manager
            else:
                frappe.local.login_manager = original_login_manager

            if original_form_dict is None:
                if hasattr(frappe, "form_dict"):
                    delattr(frappe, "form_dict")
            else:
                frappe.form_dict = original_form_dict

            frappe.local.flags.redirect_location = original_redirect_location
            frappe.set_user("Administrator")

    def test_authenticated_logout_without_login_manager_logs_error(self):
        original_login_manager = getattr(frappe.local, "login_manager", None)
        original_form_dict = getattr(frappe, "form_dict", None)
        original_redirect_location = getattr(frappe.local.flags, "redirect_location", None)

        try:
            frappe.set_user("Administrator")
            if hasattr(frappe.local, "login_manager"):
                del frappe.local.login_manager
            frappe.form_dict = frappe._dict({"redirect_to": "/"})
            frappe.local.flags.redirect_location = None

            with patch("frappe.log_error") as mocked_log_error:
                with self.assertRaises(frappe.Redirect):
                    get_context(frappe._dict())

            self.assertEqual(frappe.local.flags.redirect_location, "/")
            mocked_log_error.assert_called_once()
        finally:
            if original_login_manager is None:
                if hasattr(frappe.local, "login_manager"):
                    del frappe.local.login_manager
            else:
                frappe.local.login_manager = original_login_manager

            if original_form_dict is None:
                if hasattr(frappe, "form_dict"):
                    delattr(frappe, "form_dict")
            else:
                frappe.form_dict = original_form_dict

            frappe.local.flags.redirect_location = original_redirect_location
            frappe.set_user("Administrator")
