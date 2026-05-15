# Copyright (c) 2024, fdR and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_settings.doctype.school_calendar.school_calendar import get_events
from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestSchoolCalendar(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def _make_academic_year(self, school_name: str):
        with patch(
            "ifitwala_ed.school_settings.doctype.academic_year.academic_year.AcademicYear.create_calendar_events"
        ):
            return frappe.get_doc(
                {
                    "doctype": "Academic Year",
                    "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
                    "school": school_name,
                    "year_start_date": "2025-08-01",
                    "year_end_date": "2026-06-30",
                    "archived": 0,
                    "visible_to_admission": 1,
                }
            ).insert(ignore_permissions=True)

    def _make_calendar(self):
        organization = make_organization(prefix="Calendar Org")
        school = make_school(organization.name, prefix="Calendar School")
        academic_year = self._make_academic_year(school.name)

        with patch(
            "ifitwala_ed.school_settings.doctype.school_calendar.school_calendar.resolve_terms_for_school_calendar",
            return_value=[],
        ):
            calendar = frappe.get_doc(
                {
                    "doctype": "School Calendar",
                    "calendar_name": f"Calendar {frappe.generate_hash(length=6)}",
                    "school": school.name,
                    "academic_year": academic_year.name,
                    "holidays": [
                        {
                            "holiday_date": "2025-10-14",
                            "description": "Mid Term Break",
                        },
                        {
                            "holiday_date": "2025-08-12",
                            "description": "Opening Ceremony",
                        },
                        {
                            "holiday_date": "2025-09-01",
                            "description": "National Day",
                        },
                    ],
                }
            ).insert(ignore_permissions=True)

        calendar.reload()
        academic_year.reload()
        return calendar, academic_year

    def test_holidays_are_sorted_by_date_ascending_on_save(self):
        calendar, _academic_year = self._make_calendar()

        self.assertEqual(
            [str(row.holiday_date) for row in calendar.holidays],
            ["2025-08-12", "2025-09-01", "2025-10-14"],
        )
        self.assertEqual([row.idx for row in calendar.holidays], [1, 2, 3])

    def test_get_events_returns_empty_for_empty_calendar_filters(self):
        events = get_events("2026-03-01 00:00:00", "2026-04-12 00:00:00", filters="[]")
        self.assertEqual(events, [])

    def test_get_events_accepts_list_shaped_filters(self):
        calendar, academic_year = self._make_calendar()

        events = get_events(
            "2025-08-01 00:00:00",
            "2025-10-31 00:00:00",
            filters=json.dumps(
                [
                    ["School Calendar", "school", "=", calendar.school, 0],
                    ["School Calendar", "academic_year", "=", academic_year.name, 0],
                ]
            ),
        )

        self.assertEqual([event.title for event in events], ["Opening Ceremony", "National Day", "Mid Term Break"])
        self.assertTrue(all(event.allDay == 1 for event in events))

    def test_get_events_accepts_school_calendar_filter(self):
        calendar, _academic_year = self._make_calendar()

        events = get_events(
            "2025-08-01 00:00:00",
            "2025-10-31 00:00:00",
            filters=json.dumps([["School Calendar", "school_calendar", "=", calendar.name, 0]]),
        )

        self.assertEqual([event.title for event in events], ["Opening Ceremony", "National Day", "Mid Term Break"])
