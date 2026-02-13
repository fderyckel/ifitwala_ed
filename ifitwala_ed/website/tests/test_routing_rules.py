# ifitwala_ed/website/tests/test_routing_rules.py

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed import hooks


class TestRoutingRules(FrappeTestCase):
	"""Lock website routing contracts to avoid regressions."""

	def test_login_redirect_uses_single_hook(self):
		self.assertEqual(
			hooks.on_login,
			"ifitwala_ed.api.users.redirect_user_to_entry_portal",
		)
		self.assertFalse(hasattr(hooks, "on_session_creation"))
		self.assertFalse(hasattr(hooks, "before_request"))

	def test_website_routes_are_scoped(self):
		rules = hooks.website_route_rules
		pairs = {
			(rule.get("from_route"), rule.get("to_route"))
			for rule in rules
			if isinstance(rule, dict)
		}
		from_routes = {pair[0] for pair in pairs}

		self.assertIn(("/schools", "index"), pairs)
		self.assertIn(("/schools/<path:route>", "website"), pairs)
		self.assertIn(("/", "index"), pairs)
		self.assertIn(("/admissions", "admissions"), pairs)
		self.assertIn(("/admissions/<path:subpath>", "admissions"), pairs)
		self.assertIn(("/student", "/portal/student"), pairs)
		self.assertIn(("/staff", "/portal/staff"), pairs)
		self.assertIn(("/guardian", "/portal/guardian"), pairs)
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
		rules = hooks.website_route_rules
		pairs = {
			(rule.get("from_route"), rule.get("to_route"))
			for rule in rules
			if isinstance(rule, dict)
		}
		self.assertIn(("/inquiry", "/apply/inquiry"), pairs)
		self.assertIn(("/registration-of-interest", "/apply/registration-of-interest"), pairs)

	def test_apply_namespace_is_not_owned_by_custom_website_router(self):
		rules = hooks.website_route_rules
		from_routes = {
			rule.get("from_route")
			for rule in rules
			if isinstance(rule, dict)
		}
		self.assertNotIn("/apply", from_routes)
		self.assertNotIn("/apply/<path:subpath>", from_routes)

	def test_public_web_form_shell_assets_are_scoped(self):
		expected_css = "/assets/ifitwala_ed/css/admissions_webform_shell.css"
		expected_js = "/assets/ifitwala_ed/js/admissions_webform_shell.js"

		css_map = getattr(hooks, "webform_include_css", {})
		js_map = getattr(hooks, "webform_include_js", {})

		self.assertEqual(css_map, {"Inquiry": expected_css})
		self.assertEqual(js_map, {"Inquiry": expected_js})
