# ifitwala_ed/website/tests/test_website_route_context.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.www.index import get_context as get_index_context
from ifitwala_ed.www.website import get_context


class TestWebsiteRouteContext(FrappeTestCase):
    def test_school_website_route_uses_renderer_context(self):
        original_request = self._set_request_path("/schools/test/about")
        original_form_dict = self._set_form_dict({"preview": "1"})
        context = frappe._dict()

        try:
            with patch(
                "ifitwala_ed.www.website.build_render_context",
                return_value={
                    "seo": {"meta_title": "Preview"},
                    "template": "ifitwala_ed/website/templates/page.html",
                },
            ) as mocked_build_render_context:
                result = get_context(context)
        finally:
            self._restore_form_dict(original_form_dict)
            self._restore_request(original_request)

        self.assertEqual(result.no_cache, 1)
        self.assertEqual(result.seo["meta_title"], "Preview")
        mocked_build_render_context.assert_called_once_with(
            route="/schools/test/about",
            preview=True,
        )

    def test_root_index_redirects_when_renderer_requests_redirect(self):
        original_request = self._set_request_path("/")
        original_form_dict = self._set_form_dict({})
        original_redirect = getattr(frappe.local.flags, "redirect_location", None)
        context = frappe._dict()
        redirected_to = None

        try:
            frappe.local.flags.redirect_location = None
            with patch(
                "ifitwala_ed.www.index.build_render_context",
                return_value={"redirect_location": "/schools/demo"},
            ):
                with self.assertRaises(frappe.Redirect):
                    get_index_context(context)
            redirected_to = frappe.local.flags.redirect_location
        finally:
            self._restore_form_dict(original_form_dict)
            self._restore_request(original_request)
            frappe.local.flags.redirect_location = original_redirect

        self.assertEqual(redirected_to, "/schools/demo")

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

    def _set_form_dict(self, payload: dict):
        original = getattr(frappe.local, "form_dict", None)
        frappe.local.form_dict = frappe._dict(payload)
        return original

    def _restore_form_dict(self, original):
        if original is None:
            if hasattr(frappe.local, "form_dict"):
                del frappe.local.form_dict
            return
        frappe.local.form_dict = original
