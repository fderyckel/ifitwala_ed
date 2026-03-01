# ifitwala_ed/website/tests/test_recommendation_intake_route.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.www.admissions.recommendation.index import get_context


class TestRecommendationIntakeRoute(FrappeTestCase):
    def test_context_includes_token_and_noindex(self):
        frappe.set_user("Guest")
        original_request = self._set_request_path("/admissions/recommendation/abc123token")
        try:
            context = get_context(frappe._dict())
            self.assertEqual(context.recommendation_token, "abc123token")
            self.assertFalse(bool(context.token_missing))
            self.assertTrue(bool(context.noindex))
            self.assertTrue(bool(context.no_cache))
        finally:
            self._restore_request(original_request)
            frappe.set_user("Administrator")

    def test_context_marks_missing_token(self):
        frappe.set_user("Guest")
        original_request = self._set_request_path("/admissions/recommendation")
        try:
            context = get_context(frappe._dict())
            self.assertEqual(context.recommendation_token, "")
            self.assertTrue(bool(context.token_missing))
        finally:
            self._restore_request(original_request)
            frappe.set_user("Administrator")

    def _set_request_path(self, path: str):
        original = getattr(frappe.local, "request", None)
        frappe.local.request = frappe._dict(path=path)
        return original

    def _restore_request(self, original):
        if original is None:
            if hasattr(frappe.local, "request"):
                del frappe.local.request
            return
        frappe.local.request = original
