# ifitwala_ed/api/test_student_portfolio.py

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.student_portfolio import (
	_deterministic_share_token,
	_resolve_settings_for_school,
	_token_hash,
)


class TestStudentPortfolio(FrappeTestCase):
	def test_token_hash_is_stable_and_sha256_length(self):
		token = "abc123"
		self.assertEqual(_token_hash(token), _token_hash(token))
		self.assertEqual(len(_token_hash(token)), 64)

	def test_deterministic_share_token_is_repeatable(self):
		token_a = _deterministic_share_token(portfolio="SPF-001", user="test@example.com", idempotency_key="idem-1")
		token_b = _deterministic_share_token(portfolio="SPF-001", user="test@example.com", idempotency_key="idem-1")
		token_c = _deterministic_share_token(portfolio="SPF-001", user="test@example.com", idempotency_key="idem-2")
		self.assertEqual(token_a, token_b)
		self.assertNotEqual(token_a, token_c)

	def test_settings_defaults_without_school(self):
		settings = _resolve_settings_for_school(None)
		self.assertEqual(settings.get("enable_moderation"), 1)
		self.assertEqual(settings.get("moderation_scope"), "Showcase only")
		self.assertEqual(settings.get("allow_student_external_share"), 1)
