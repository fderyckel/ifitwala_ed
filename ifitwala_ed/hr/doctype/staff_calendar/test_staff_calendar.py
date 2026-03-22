# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.hr.doctype.staff_calendar.staff_calendar import StaffCalendar


class TestStaffCalendar(FrappeTestCase):
    def test_get_supported_countries_returns_unavailable_payload_when_dependency_is_missing(self):
        doc = frappe.get_doc({"doctype": "Staff Calendar"})

        def fake_import_module(name):
            exc = ModuleNotFoundError("No module named 'holidays'")
            exc.name = "holidays"
            raise exc

        with patch(
            "ifitwala_ed.hr.doctype.staff_calendar.staff_calendar.importlib.import_module",
            side_effect=fake_import_module,
        ):
            result = doc.get_supported_countries()

        self.assertFalse(result["available"])
        self.assertEqual(result["countries"], [])
        self.assertEqual(result["subdivisions_by_country"], {})
        self.assertIn("Install the app Python dependencies", result["message"])

    def test_get_country_holidays_raises_actionable_error_when_dependency_is_missing(self):
        doc = frappe.get_doc(
            {
                "doctype": "Staff Calendar",
                "country": "TH",
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
            }
        )

        def fake_import_module(name):
            exc = ModuleNotFoundError("No module named 'holidays'")
            exc.name = "holidays"
            raise exc

        with (
            patch.object(StaffCalendar, "_ensure_saved", return_value=None),
            patch(
                "ifitwala_ed.hr.doctype.staff_calendar.staff_calendar.importlib.import_module",
                side_effect=fake_import_module,
            ),
            self.assertRaises(frappe.ValidationError) as exc,
        ):
            doc.get_country_holidays()

        self.assertIn("Install the app Python dependencies", str(exc.exception))
