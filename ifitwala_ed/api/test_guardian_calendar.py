from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.guardian_calendar import (
    _fetch_guardian_holiday_items,
    get_guardian_calendar_overlay,
)


class TestGuardianCalendarOverlay(FrappeTestCase):
    def test_calendar_overlay_rejects_out_of_scope_school_filter(self):
        context = {
            "children": [
                {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            ],
            "student_names": ["STU-1"],
        }

        with patch(
            "ifitwala_ed.api.guardian_calendar._resolve_guardian_communication_context",
            return_value=context,
        ):
            with self.assertRaises(frappe.PermissionError):
                get_guardian_calendar_overlay(month_start="2026-04-01", school="SCHOOL-404")

    def test_calendar_overlay_returns_month_summary_and_filter_options(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-2"},
        ]
        school_event_rows = [
            {
                "kind": "school_event",
                "item_id": "event::EVENT-1",
                "matched_children": [children[0]],
                "school_event": {
                    "name": "EVENT-1",
                    "subject": "Parent Conference",
                    "school": "SCHOOL-1",
                    "description": "Meet teachers in person.",
                    "event_category": "Meeting",
                    "starts_on": "2026-04-15T09:00:00",
                    "ends_on": "2026-04-15T11:00:00",
                    "all_day": 0,
                },
            }
        ]
        holiday_rows = [
            {
                "item_id": "holiday::CAL-1::2026-04-18",
                "kind": "holiday",
                "title": "Songkran Break",
                "start": "2026-04-18",
                "end": "2026-04-18",
                "all_day": True,
                "color": "#dc2626",
                "school": "SCHOOL-1",
                "matched_children": [children[0]],
                "description": "School closed.",
                "event_category": None,
                "open_target": None,
            }
        ]

        with (
            patch(
                "ifitwala_ed.api.guardian_calendar.now_datetime",
                return_value=frappe.utils.get_datetime("2026-04-20 09:00:00"),
            ),
            patch(
                "ifitwala_ed.api.guardian_calendar._resolve_guardian_communication_context",
                return_value={
                    "children": children,
                    "student_names": ["STU-1", "STU-2"],
                },
            ),
            patch(
                "ifitwala_ed.api.guardian_calendar._fetch_guardian_holiday_items",
                return_value=holiday_rows,
            ) as holiday_mock,
            patch(
                "ifitwala_ed.api.guardian_calendar._fetch_guardian_school_events",
                return_value=school_event_rows,
            ) as event_mock,
        ):
            payload = get_guardian_calendar_overlay(
                month_start="2026-04-20",
                student="STU-1",
                include_holidays=1,
                include_school_events=1,
            )

        holiday_mock.assert_called_once()
        event_mock.assert_called_once()
        self.assertEqual(payload["meta"]["month_start"], "2026-04-01")
        self.assertEqual(payload["meta"]["month_end"], "2026-04-30")
        self.assertEqual(payload["meta"]["filters"]["student"], "STU-1")
        self.assertEqual(payload["filter_options"]["students"], children)
        self.assertEqual(
            payload["filter_options"]["schools"],
            [{"school": "SCHOOL-1", "label": "SCHOOL-1"}],
        )
        self.assertEqual(payload["summary"], {"holiday_count": 1, "school_event_count": 1})
        self.assertEqual([item["kind"] for item in payload["items"]], ["holiday", "school_event"])
        self.assertEqual(payload["items"][1]["open_target"], {"type": "school-event", "name": "EVENT-1"})

    def test_fetch_guardian_holiday_items_matches_children_to_resolved_calendars(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-1"},
        ]
        context = {
            "children": children,
            "child_by_student": {row["student"]: row for row in children},
            "student_names": ["STU-1", "STU-2"],
            "student_school_names": {
                "STU-1": {"SCHOOL-1"},
                "STU-2": {"SCHOOL-1"},
            },
        }

        with (
            patch(
                "ifitwala_ed.api.guardian_calendar.resolve_school_calendars_for_window",
                return_value=[
                    {
                        "name": "CAL-PRIMARY",
                        "school": "SCHOOL-1",
                        "academic_year": "AY-1",
                    }
                ],
            ),
            patch.object(
                frappe,
                "get_all",
                return_value=[
                    {
                        "parent": "CAL-PRIMARY",
                        "holiday_date": "2026-04-18",
                        "description": "School closed",
                        "color": "#ef4444",
                    }
                ],
            ),
        ):
            items = _fetch_guardian_holiday_items(
                context,
                month_start=frappe.utils.getdate("2026-04-01"),
                month_end=frappe.utils.getdate("2026-04-30"),
            )

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "School closed")
        self.assertEqual(items[0]["matched_children"], children)
        self.assertEqual(items[0]["school"], "SCHOOL-1")
