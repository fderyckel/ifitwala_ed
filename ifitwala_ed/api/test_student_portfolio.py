# ifitwala_ed/api/test_student_portfolio.py

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.student_portfolio import (
    _deterministic_share_token,
    _load_item_evidence,
    _moderation_state_for_action,
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

    def test_moderation_state_for_action(self):
        self.assertEqual(_moderation_state_for_action("approve"), "Approved")
        self.assertEqual(_moderation_state_for_action("return_for_edit"), "Returned for Edit")
        self.assertEqual(_moderation_state_for_action("hide"), "Hidden / Rejected")

    @patch("ifitwala_ed.api.student_portfolio.frappe.get_all")
    def test_load_item_evidence_wraps_external_file_urls(self, mock_get_all):
        mock_get_all.return_value = [
            {
                "name": "FILE-EXT-1",
                "file_name": "portfolio-work.png",
                "file_url": "/private/files/portfolio-work.png",
                "file_size": 128,
            }
        ]

        evidence = _load_item_evidence(
            [
                {
                    "item_name": "SPI-001",
                    "item_type": "External Artefact",
                    "artefact_file": "FILE-EXT-1",
                }
            ]
        )

        row = evidence.get("SPI-001") or {}
        secure_url = (row.get("file_url") or "").strip()
        self.assertTrue(secure_url)

        parsed = urlparse(secure_url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_academic_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-EXT-1")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Student Portfolio Item")
        self.assertEqual((query.get("context_name") or [None])[0], "SPI-001")
