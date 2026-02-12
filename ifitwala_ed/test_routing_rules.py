# ifitwala_ed/test_routing_rules.py

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed import hooks


class TestRoutingRules(FrappeTestCase):
	"""Lock core routing contracts to avoid regressions."""

	def test_login_redirect_uses_single_hook(self):
		"""Only on_login should enforce post-login portal redirects."""
		self.assertEqual(
			hooks.on_login,
			"ifitwala_ed.api.users.redirect_user_to_entry_portal",
		)
		self.assertFalse(hasattr(hooks, "on_session_creation"))
		self.assertFalse(hasattr(hooks, "before_request"))

	def test_public_web_forms_are_explicitly_preserved(self):
		"""Public inquiry routes must bypass website catch-all routing."""
		rules = hooks.website_route_rules
		pairs = {
			(rule.get("from_route"), rule.get("to_route"))
			for rule in rules
			if isinstance(rule, dict)
		}
		self.assertIn(("/inquiry", "/inquiry"), pairs)
		self.assertIn(("/inquiry/new", "/inquiry/new"), pairs)
		self.assertIn(
			("/registration-of-interest", "/registration-of-interest"),
			pairs,
		)
		self.assertIn(
			("/registration-of-interest/new", "/registration-of-interest/new"),
			pairs,
		)

	def test_public_web_forms_allow_guest_access(self):
		"""Public admissions forms must remain anonymous for guests."""
		app_path = frappe.get_app_path("ifitwala_ed")
		configs = [
			("inquiry", "admission/web_form/inquiry/inquiry.json"),
			(
				"registration-of-interest",
				"admission/web_form/registration_of_interest/registration_of_interest.json",
			),
		]
		for route, relative_path in configs:
			with open(os.path.join(app_path, relative_path), "r", encoding="utf-8") as f:
				payload = json.load(f)
			self.assertEqual(payload.get("anonymous"), 1, f"{route} must be anonymous")
			self.assertEqual(payload.get("published"), 1, f"{route} must stay published")
