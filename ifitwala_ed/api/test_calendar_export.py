from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch

import frappe
import pytz

from ifitwala_ed.api.calendar_export import (
    PDF_OPTIONS,
    _build_timetable_weeks,
    _format_date_span,
    _render_staff_timetable_pdf,
    _resolve_brand_context,
    _resolve_staff_timetable_window,
    export_staff_timetable_pdf,
)


class TestCalendarExport(TestCase):
    def test_resolve_staff_timetable_window_uses_next_calendar_month_for_month_preset(self):
        window = _resolve_staff_timetable_window("next_month", date(2026, 4, 20))

        self.assertEqual(window["preset"], "next_month")
        self.assertEqual(window["start_date"], date(2026, 5, 1))
        self.assertEqual(window["end_date_exclusive"], date(2026, 6, 1))

    def test_resolve_staff_timetable_window_expands_current_week_for_two_week_preset(self):
        window = _resolve_staff_timetable_window("next_2_weeks", date(2026, 4, 22))

        self.assertEqual(window["start_date"], date(2026, 4, 20))
        self.assertEqual(window["end_date_exclusive"], date(2026, 5, 4))

    def test_format_date_span_uses_human_readable_ordinal_dates(self):
        label = _format_date_span(date(2026, 4, 20), date(2026, 5, 3))

        self.assertEqual(label, "20th April to 3rd May 2026")

    def test_build_timetable_weeks_expands_multi_day_events_and_sorts_timed_events(self):
        tzinfo = pytz.timezone("UTC")
        weeks = _build_timetable_weeks(
            events=[
                {
                    "title": "Spring Festival",
                    "start": "2026-05-05T00:00:00+00:00",
                    "end": "2026-05-07T00:00:00+00:00",
                    "allDay": True,
                    "source": "school_event",
                    "color": "#2A9D8F",
                    "meta": {"location": "Main Hall"},
                },
                {
                    "title": "Math 7A",
                    "start": "2026-05-05T08:00:00+00:00",
                    "end": "2026-05-05T08:45:00+00:00",
                    "allDay": False,
                    "source": "student_group",
                    "color": "#2563EB",
                    "meta": {"location": "Room 201"},
                },
                {
                    "title": "Leadership Meeting",
                    "start": "2026-05-05T13:00:00+00:00",
                    "end": "2026-05-05T14:00:00+00:00",
                    "allDay": False,
                    "source": "meeting",
                    "color": "#7C3AED",
                    "meta": {"location": "Board Room"},
                },
            ],
            start_date=date(2026, 5, 5),
            end_date_exclusive=date(2026, 5, 8),
            tzinfo=tzinfo,
        )

        self.assertEqual(len(weeks), 1)
        tuesday = next(day for day in weeks[0]["days"] if day["iso"] == "2026-05-05")
        wednesday = next(day for day in weeks[0]["days"] if day["iso"] == "2026-05-06")

        self.assertEqual(len(tuesday["all_day_events"]), 1)
        self.assertEqual(tuesday["all_day_events"][0]["title"], "Spring Festival")
        self.assertEqual([event["title"] for event in tuesday["timed_events"]], ["Math 7A", "Leadership Meeting"])
        self.assertEqual(tuesday["timed_events"][0]["time_label"], "08:00 - 08:45")
        self.assertEqual(len(wednesday["all_day_events"]), 1)

    def test_build_timetable_weeks_can_hide_weekend_columns(self):
        tzinfo = pytz.timezone("UTC")
        weeks = _build_timetable_weeks(
            events=[
                {
                    "title": "Friday Meeting",
                    "start": "2026-05-08T09:00:00+00:00",
                    "end": "2026-05-08T09:30:00+00:00",
                    "allDay": False,
                    "source": "meeting",
                    "color": "#7C3AED",
                    "meta": {"location": "Library"},
                },
                {
                    "title": "Saturday Open House",
                    "start": "2026-05-09T09:00:00+00:00",
                    "end": "2026-05-09T12:00:00+00:00",
                    "allDay": False,
                    "source": "school_event",
                    "color": "#2A9D8F",
                    "meta": {"location": "Courtyard"},
                },
            ],
            start_date=date(2026, 5, 4),
            end_date_exclusive=date(2026, 5, 11),
            tzinfo=tzinfo,
            include_weekends=False,
        )

        self.assertEqual(len(weeks), 1)
        self.assertEqual([day["weekday_short"] for day in weeks[0]["days"]], ["Mon", "Tue", "Wed", "Thu", "Fri"])
        self.assertEqual(weeks[0]["event_count"], 1)
        self.assertNotIn("2026-05-09", [day["iso"] for day in weeks[0]["days"]])

    def test_resolve_brand_context_falls_back_to_parent_school_logo_and_tagline(self):
        with (
            patch(
                "ifitwala_ed.api.calendar_export.get_ancestor_schools", return_value=["SCHOOL-CHILD", "SCHOOL-PARENT"]
            ),
            patch("ifitwala_ed.api.calendar_export.get_ancestor_organizations", return_value=["ORG-1"]),
            patch("ifitwala_ed.api.calendar_export.frappe.db.get_value") as mock_get_value,
            patch("ifitwala_ed.api.calendar_export.frappe.get_all") as mock_get_all,
        ):
            mock_get_value.side_effect = [
                {
                    "name": "SCHOOL-CHILD",
                    "school_name": "Lwitwala International School",
                    "school_logo": "",
                    "school_tagline": "",
                    "organization": "ORG-1",
                },
                {
                    "name": "ORG-1",
                    "organization_name": "Ifitwala Education Group",
                    "organization_logo": "https://org.example/logo.png",
                },
            ]
            mock_get_all.side_effect = [
                [
                    {
                        "name": "SCHOOL-CHILD",
                        "school_name": "Lwitwala International School",
                        "school_logo": "",
                        "school_tagline": "",
                    },
                    {
                        "name": "SCHOOL-PARENT",
                        "school_name": "Ifitwala Secondary School",
                        "school_logo": "https://school.example/logo.png",
                        "school_tagline": "Where talent meets opportunities",
                    },
                ],
                [
                    {
                        "name": "ORG-1",
                        "organization_name": "Ifitwala Education Group",
                        "organization_logo": "https://org.example/logo.png",
                    }
                ],
            ]

            brand = _resolve_brand_context(
                employee={"school": "SCHOOL-CHILD", "organization": "ORG-1"},
                events=[],
            )

        self.assertEqual(brand["brand_name"], "Lwitwala International School")
        self.assertEqual(brand["tagline"], "Where talent meets opportunities")
        self.assertEqual(brand["logo_url"], "https://school.example/logo.png")

    def test_render_staff_timetable_pdf_passes_landscape_options(self):
        with patch("frappe.utils.pdf.get_pdf", return_value=b"%PDF-landscape") as get_pdf_mock:
            result = _render_staff_timetable_pdf("<html />")

        self.assertEqual(result, b"%PDF-landscape")
        get_pdf_mock.assert_called_once_with("<html />", options=PDF_OPTIONS)

    def test_export_staff_timetable_pdf_sets_inline_pdf_response(self):
        with (
            patch("ifitwala_ed.api.calendar_export._system_tzinfo", return_value=pytz.timezone("UTC")),
            patch("ifitwala_ed.api.calendar_export.now_datetime", return_value=datetime(2026, 4, 20, 9, 0, 0)),
            patch(
                "ifitwala_ed.api.calendar_export._resolve_employee_for_user",
                return_value={
                    "employee_full_name": "Ada Staff",
                    "designation": "Teacher",
                    "employee_group": "Academic Staff",
                    "school": "SCHOOL-1",
                    "organization": "ORG-1",
                },
            ),
            patch(
                "ifitwala_ed.api.calendar_export.calendar_staff_feed.get_staff_calendar",
                return_value={"events": [], "counts": {}},
            ),
            patch(
                "ifitwala_ed.api.calendar_export._build_staff_timetable_context",
                return_value={"weeks": [], "count_cards": []},
            ),
            patch("ifitwala_ed.api.calendar_export._render_staff_timetable_export_html", return_value="<html />"),
            patch("ifitwala_ed.api.calendar_export._render_staff_timetable_pdf", return_value=b"%PDF-test"),
        ):
            frappe.local.response = {}
            frappe.session.user = "staff@example.com"

            export_staff_timetable_pdf("next_2_weeks")

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")
        self.assertEqual(frappe.local.response.get("content_type"), "application/pdf")
        self.assertEqual(frappe.local.response.get("filecontent"), b"%PDF-test")
        self.assertIn("staff-timetable-next_2_weeks-2026-04-20.pdf", frappe.local.response.get("filename"))
