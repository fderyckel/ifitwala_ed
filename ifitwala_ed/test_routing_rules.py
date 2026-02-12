# ifitwala_ed/test_routing_rules.py

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
		self.assertIn(
			("/registration-of-interest", "/registration-of-interest"),
			pairs,
		)
