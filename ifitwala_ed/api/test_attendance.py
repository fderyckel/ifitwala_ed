# ifitwala_ed/api/test_attendance.py

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api.attendance import (
    _clean_optional,
    _hash_list,
    _normalize_heatmap_mode,
    _normalize_thresholds,
)


class TestAttendanceApi(TestCase):
    @patch("ifitwala_ed.api.attendance._resolve_school_threshold_defaults")
    def test_normalize_thresholds_uses_school_defaults_not_client_override(self, mock_defaults):
        mock_defaults.return_value = (92.0, 81.0)

        payload = _normalize_thresholds(
            {"warning": 10, "critical": 5},
            selected_school="SCH-1",
        )

        self.assertEqual(payload, {"warning": 92.0, "critical": 81.0})

    @patch("ifitwala_ed.api.attendance._resolve_school_threshold_defaults")
    def test_normalize_thresholds_swaps_when_warning_below_critical(self, mock_defaults):
        mock_defaults.return_value = (70.0, 85.0)

        payload = _normalize_thresholds(None, selected_school="SCH-1")

        self.assertEqual(payload, {"warning": 85.0, "critical": 70.0})

    def test_normalize_heatmap_mode_defaults_to_block(self):
        self.assertEqual(_normalize_heatmap_mode("day"), "day")
        self.assertEqual(_normalize_heatmap_mode("invalid"), "block")

    def test_clean_optional_and_hash_list_helpers(self):
        self.assertEqual(_clean_optional("  abc  "), "abc")
        self.assertIsNone(_clean_optional("   "))
        self.assertNotEqual(_hash_list(["a", "b"]), _hash_list(["a", "c"]))
