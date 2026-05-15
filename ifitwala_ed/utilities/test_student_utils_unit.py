from __future__ import annotations

import sys
from datetime import date
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _getdate(value=None):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


class TestStudentUtilsUnit(TestCase):
    def test_format_student_age_uses_years_and_months(self):
        with stubbed_frappe() as frappe:
            frappe.utils = sys.modules["frappe.utils"]
            frappe.utils.getdate = _getdate
            frappe.utils.today = lambda: "2026-04-20"
            module = import_fresh("ifitwala_ed.utilities.student_utils")

            age = module.format_student_age("2012-01-15")

        self.assertEqual(age, "14 years, 3 months")

    def test_birthday_context_returns_label_without_dob(self):
        with stubbed_frappe() as frappe:
            frappe.utils = sys.modules["frappe.utils"]
            frappe.utils.getdate = _getdate
            frappe.utils.today = lambda: "2026-03-20"
            module = import_fresh("ifitwala_ed.utilities.student_utils")

            payload = module.get_birthday_context("2014-03-23", window_days=4)

        self.assertEqual(
            payload,
            {
                "birthday_in_window": True,
                "birthday_today": False,
                "birthday_label": "March 23",
            },
        )
