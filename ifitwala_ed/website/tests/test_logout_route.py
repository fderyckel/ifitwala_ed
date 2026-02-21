# ifitwala_ed/website/tests/test_logout_route.py

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.www.logout import _safe_redirect_target


class TestLogoutRoute(FrappeTestCase):
    def test_safe_redirect_target_allows_internal_absolute_paths(self):
        self.assertEqual(_safe_redirect_target("/"), "/")
        self.assertEqual(_safe_redirect_target("/login?redirect-to=/admissions"), "/login?redirect-to=/admissions")

    def test_safe_redirect_target_blocks_external_or_relative_values(self):
        self.assertEqual(_safe_redirect_target("https://example.com"), "/")
        self.assertEqual(_safe_redirect_target("//example.com"), "/")
        self.assertEqual(_safe_redirect_target("login"), "/")
