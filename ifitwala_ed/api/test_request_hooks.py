# ifitwala_ed/api/test_request_hooks.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase
from werkzeug.wrappers import Response

from ifitwala_ed import hooks
from ifitwala_ed.request_hooks import apply_default_security_headers


class TestRequestHooks(FrappeTestCase):
    def test_after_request_hook_is_registered(self):
        self.assertIn("ifitwala_ed.request_hooks.apply_default_security_headers", hooks.after_request)

    def test_apply_default_security_headers_sets_nosniff(self):
        response = Response("ok")

        updated_response = apply_default_security_headers(response)

        self.assertEqual(updated_response.headers.get("X-Content-Type-Options"), "nosniff")

    def test_apply_default_security_headers_preserves_existing_value(self):
        response = Response("ok")
        response.headers["X-Content-Type-Options"] = "nosniff"

        updated_response = apply_default_security_headers(response)

        self.assertEqual(updated_response.headers.get("X-Content-Type-Options"), "nosniff")
