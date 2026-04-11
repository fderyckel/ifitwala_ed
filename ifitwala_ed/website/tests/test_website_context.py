# ifitwala_ed/website/tests/test_website_context.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.website.context import update_website_context


class TestWebsiteContext(FrappeTestCase):
    def test_login_context_uses_public_brand_identity(self):
        original_request = getattr(frappe.local, "request", None)
        frappe.local.request = frappe._dict(path="/login")

        try:
            with patch(
                "ifitwala_ed.website.context.get_public_brand_identity",
                return_value={
                    "brand_name": "Root Org",
                    "brand_logo": "/files/root-org.png",
                },
            ):
                values = update_website_context(frappe._dict({"logo": "/files/legacy.png"}))
        finally:
            if original_request is None:
                del frappe.local.request
            else:
                frappe.local.request = original_request

        self.assertEqual(
            values,
            {
                "app_name": "Root Org",
                "logo": "/files/root-org.png",
            },
        )

    def test_non_login_route_does_not_override_branding(self):
        original_request = getattr(frappe.local, "request", None)
        frappe.local.request = frappe._dict(path="/schools")

        try:
            values = update_website_context(frappe._dict())
        finally:
            if original_request is None:
                del frappe.local.request
            else:
                frappe.local.request = original_request

        self.assertEqual(values, {})
