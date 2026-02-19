# ifitwala_ed/website/tests/test_routing_rules.py

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed import hooks


class TestRoutingRules(FrappeTestCase):
    """Lock website routing contracts to avoid regressions."""

    def test_login_redirect_hooks_share_single_owner(self):
        self.assertEqual(
            hooks.on_login,
            "ifitwala_ed.api.users.redirect_user_to_entry_portal",
        )
        self.assertEqual(
            hooks.on_session_creation,
            "ifitwala_ed.api.users.redirect_user_to_entry_portal",
        )
        self.assertEqual(
            hooks.get_website_user_home_page,
            "ifitwala_ed.api.users.get_website_user_home_page",
        )
        self.assertEqual(
            hooks.before_request,
            ["ifitwala_ed.api.users.sanitize_login_redirect_param"],
        )

    def test_website_routes_are_scoped(self):
        rules = hooks.website_route_rules
        pairs = {(rule.get("from_route"), rule.get("to_route")) for rule in rules if isinstance(rule, dict)}
        from_routes = {pair[0] for pair in pairs}

        self.assertIn(("/schools", "index"), pairs)
        self.assertIn(("/schools/<path:route>", "website"), pairs)
        self.assertIn(("/", "index"), pairs)
        self.assertIn(("/admissions", "admissions"), pairs)
        self.assertIn(("/admissions/<path:subpath>", "admissions"), pairs)
        self.assertIn(("/student", "portal"), pairs)
        self.assertIn(("/student/<path:subpath>", "portal"), pairs)
        self.assertIn(("/staff", "portal"), pairs)
        self.assertIn(("/staff/<path:subpath>", "portal"), pairs)
        self.assertIn(("/guardian", "portal"), pairs)
        self.assertIn(("/guardian/<path:subpath>", "portal"), pairs)
        self.assertIn(("/portal", "portal"), pairs)
        self.assertIn(("/portal/<path:subpath>", "portal"), pairs)
        self.assertNotIn("/inquiry", from_routes)
        self.assertNotIn("/registration-of-interest", from_routes)
        self.assertNotIn("/<path:route>", from_routes)

    def test_public_web_forms_are_namespaced_under_apply(self):
        app_path = frappe.get_app_path("ifitwala_ed")
        configs = [
            ("inquiry", "apply/inquiry", "admission/web_form/inquiry/inquiry.json"),
            (
                "registration-of-interest",
                "apply/registration-of-interest",
                "admission/web_form/registration_of_interest/registration_of_interest.json",
            ),
        ]
        for route_name, expected_route, relative_path in configs:
            with open(os.path.join(app_path, relative_path), "r", encoding="utf-8") as f:
                payload = json.load(f)
            self.assertEqual(payload.get("anonymous"), 1, f"{route_name} must be anonymous")
            self.assertEqual(payload.get("published"), 1, f"{route_name} must stay published")
            self.assertEqual(payload.get("route"), expected_route, f"{route_name} route drifted")

    def test_legacy_public_form_aliases_forward_to_apply_namespace(self):
        redirects = getattr(hooks, "website_redirects", []) or []
        pairs = {(row.get("source"), row.get("target")) for row in redirects if isinstance(row, dict)}
        lookup = {row.get("source"): row for row in redirects if isinstance(row, dict) and row.get("source")}
        self.assertIn(("/inquiry", "/apply/inquiry"), pairs)
        self.assertIn(("/registration-of-interest", "/apply/registration-of-interest"), pairs)
        self.assertEqual(lookup["/inquiry"].get("redirect_http_status"), 301)
        self.assertEqual(lookup["/registration-of-interest"].get("redirect_http_status"), 301)

    def test_legacy_top_level_paths_redirect_to_canonical_portal_namespace(self):
        redirects = getattr(hooks, "website_redirects", []) or []
        pairs = {(row.get("source"), row.get("target")) for row in redirects if isinstance(row, dict)}
        lookup = {row.get("source"): row for row in redirects if isinstance(row, dict) and row.get("source")}
        self.assertIn(("/student", "/portal/student"), pairs)
        self.assertIn(("/staff", "/portal/staff"), pairs)
        self.assertIn(("/guardian", "/portal/guardian"), pairs)
        self.assertEqual(lookup["/student"].get("redirect_http_status"), 301)
        self.assertEqual(lookup["/staff"].get("redirect_http_status"), 301)
        self.assertEqual(lookup["/guardian"].get("redirect_http_status"), 301)

    def test_apply_namespace_is_not_owned_by_custom_website_router(self):
        rules = hooks.website_route_rules
        from_routes = {rule.get("from_route") for rule in rules if isinstance(rule, dict)}
        self.assertNotIn("/apply", from_routes)
        self.assertNotIn("/apply/<path:subpath>", from_routes)

    def test_public_web_form_shell_assets_are_scoped(self):
        expected_css = "public/css/admissions_webform_shell.css"
        expected_js = "public/js/admissions_webform_shell.js"

        css_map = getattr(hooks, "webform_include_css", {})
        js_map = getattr(hooks, "webform_include_js", {})

        self.assertEqual(
            css_map,
            {
                "Inquiry": expected_css,
                "Registration of Interest": expected_css,
            },
        )
        self.assertEqual(
            js_map,
            {
                "Inquiry": expected_js,
                "Registration of Interest": expected_js,
            },
        )
