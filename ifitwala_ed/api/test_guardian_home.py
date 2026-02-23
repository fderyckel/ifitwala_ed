# ifitwala_ed/api/test_guardian_home.py

from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.guardian_home import (
    _assert_no_internal_schedule_keys,
    _find_forbidden_keys,
    _resolve_chip_status,
)


class TestGuardianHome(FrappeTestCase):
    def test_resolve_chip_status_respects_availability_and_lock_window(self):
        anchor = date(2026, 2, 2)

        self.assertEqual(
            _resolve_chip_status(
                outcome=None,
                due=date(2026, 2, 5),
                anchor=anchor,
                available_from=date(2026, 2, 4),
                lock_date=None,
            ),
            "assigned",
        )
        self.assertEqual(
            _resolve_chip_status(
                outcome=None,
                due=date(2026, 2, 1),
                anchor=anchor,
                available_from=None,
                lock_date=date(2026, 2, 4),
            ),
            "assigned",
        )
        self.assertEqual(
            _resolve_chip_status(
                outcome=None,
                due=date(2026, 2, 1),
                anchor=anchor,
                available_from=None,
                lock_date=date(2026, 2, 1),
            ),
            "missing",
        )

    def test_forbidden_key_detection_finds_rotation_and_block(self):
        payload = {
            "zones": {
                "family_timeline": [
                    {
                        "children": [
                            {
                                "rotation_day": 1,
                                "blocks": [{"title": "Class", "block_number": 2}],
                            }
                        ]
                    }
                ]
            }
        }
        found = _find_forbidden_keys(payload)
        self.assertTrue(any(path.endswith(".rotation_day") for path in found))
        self.assertTrue(any(path.endswith(".block_number") for path in found))

    def test_assert_no_internal_schedule_keys_throws_in_debug(self):
        payload = {"zones": {"family_timeline": [{"rotation_day": 1}]}}
        warnings: list[str] = []

        with self.assertRaises(frappe.ValidationError):
            _assert_no_internal_schedule_keys(payload=payload, debug_mode=True, debug_warnings=warnings)

        self.assertEqual(warnings, [])

    def test_assert_no_internal_schedule_keys_warns_when_not_debug(self):
        payload = {"zones": {"family_timeline": [{"block_number": 2}]}}
        warnings: list[str] = []

        _assert_no_internal_schedule_keys(payload=payload, debug_mode=False, debug_warnings=warnings)
        self.assertEqual(len(warnings), 1)
        self.assertIn("guardian_home_forbidden_keys_detected", warnings[0])
