# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.hr.doctype.staff_calendar.staff_calendar import StaffCalendar, get_events


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

    def test_get_events_requires_explicit_scope(self):
        with self.assertRaises(frappe.ValidationError) as exc:
            get_events("2026-03-01", "2026-03-31", "[]")

        self.assertIn("Select a Staff Calendar or filter by both School and Employee Group", str(exc.exception))

    def test_get_events_parses_calendar_filter_rows(self):
        filters = json.dumps(
            [
                ["Staff Calendar", "school", "=", "Lamai School"],
                ["Staff Calendar", "employee_group", "=", "Teachers"],
                ["Staff Calendar", "academic_year", "=", "AY-2026"],
            ]
        )

        with (
            patch(
                "ifitwala_ed.hr.doctype.staff_calendar.staff_calendar.frappe.get_all",
                return_value=["SC-2026"],
            ) as get_all,
            patch(
                "ifitwala_ed.hr.doctype.staff_calendar.staff_calendar.frappe.get_list",
                return_value=[
                    frappe._dict(
                        name="HOL-1",
                        staff_calendar="SC-2026",
                        holiday_date="2026-03-12",
                        description="Founders Day",
                        color="#ff0",
                    )
                ],
            ) as get_list,
        ):
            events = get_events("2026-03-01", "2026-03-31", filters)

        self.assertEqual(
            get_all.call_args.kwargs["filters"],
            {
                "school": "Lamai School",
                "employee_group": "Teachers",
                "academic_year": "AY-2026",
                "to_date": [">=", frappe.utils.getdate("2026-03-01")],
                "from_date": ["<=", frappe.utils.getdate("2026-03-31")],
            },
        )
        self.assertEqual(
            get_list.call_args.kwargs["filters"][0], ["Staff Calendar Holidays", "parent", "in", ["SC-2026"]]
        )
        self.assertEqual(events[0]["title"], "Founders Day")
        self.assertEqual(events[0]["start"], "2026-03-12")
        self.assertEqual(events[0]["allDay"], 1)

    def test_get_events_accepts_direct_staff_calendar_filter(self):
        filters = json.dumps([{"fieldname": "staff_calendar", "value": "SC-2026"}])

        with (
            patch("ifitwala_ed.hr.doctype.staff_calendar.staff_calendar.frappe.get_all") as get_all,
            patch(
                "ifitwala_ed.hr.doctype.staff_calendar.staff_calendar.frappe.get_list",
                return_value=[
                    frappe._dict(
                        name="HOL-2",
                        staff_calendar="SC-2026",
                        holiday_date="2026-03-18",
                        description="Sports Day",
                        color="#0ff",
                    )
                ],
            ),
        ):
            events = get_events("2026-03-01", "2026-03-31", filters)

        get_all.assert_not_called()
        self.assertEqual(events[0]["description"], "Sports Day")
        self.assertEqual(events[0]["end"], "2026-03-18")
