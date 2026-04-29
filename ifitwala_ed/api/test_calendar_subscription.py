from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import frappe
import pytz

from ifitwala_ed.api import calendar_subscription


class TestCalendarSubscription(TestCase):
    def test_staff_subscription_ics_filters_weekly_off_and_escapes_event_text(self):
        tzinfo = pytz.timezone("UTC")
        payload = {
            "events": [
                {
                    "id": "meeting::MTG-1",
                    "title": "Budget, Review; Term\nLine",
                    "start": "2026-04-28T09:00:00+00:00",
                    "end": "2026-04-28T10:00:00+00:00",
                    "allDay": False,
                    "source": "meeting",
                    "meta": {"location": "Room, 12"},
                },
                {
                    "id": "staff_holiday::CAL::2026-05-01",
                    "title": "Weekly Off",
                    "start": "2026-05-01T00:00:00+00:00",
                    "end": "2026-05-02T00:00:00+00:00",
                    "allDay": True,
                    "source": "staff_holiday",
                    "meta": {"weekly_off": 1},
                },
                {
                    "id": "staff_holiday::CAL::2026-05-04",
                    "title": "Public Holiday",
                    "start": "2026-05-04T00:00:00+00:00",
                    "end": "2026-05-05T00:00:00+00:00",
                    "allDay": True,
                    "source": "staff_holiday",
                    "meta": {"weekly_off": 0},
                },
            ]
        }

        with (
            patch("ifitwala_ed.api.calendar_subscription._system_tzinfo", return_value=tzinfo),
            patch("ifitwala_ed.api.calendar_subscription.now_datetime", return_value=datetime(2026, 4, 28, 8, 0, 0)),
            patch("ifitwala_ed.api.calendar_subscription.frappe.utils.get_url", return_value="https://school.example"),
        ):
            ics = calendar_subscription.build_staff_calendar_ics(payload=payload, subscription={"name": "SUB-1"})

        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("REFRESH-INTERVAL;VALUE=DURATION:PT1H", ics)
        self.assertIn("SUMMARY:Budget\\, Review\\; Term\\nLine", ics)
        self.assertIn("LOCATION:Room\\, 12", ics)
        self.assertIn("SUMMARY:Public Holiday", ics)
        self.assertNotIn("SUMMARY:Weekly Off", ics)
        self.assertIn("DTSTART:20260428T090000Z", ics)
        self.assertIn("DTSTART;VALUE=DATE:20260504", ics)

    def test_download_staff_calendar_subscription_sets_ics_response_without_fetch_writes(self):
        tzinfo = pytz.timezone("UTC")
        window_start = tzinfo.localize(datetime(2026, 4, 1, 0, 0, 0))
        window_end = tzinfo.localize(datetime(2027, 4, 29, 0, 0, 0))

        with (
            patch(
                "ifitwala_ed.api.calendar_subscription._resolve_subscription_token",
                return_value={"name": "SUB-1", "user": "staff@example.com"},
            ),
            patch(
                "ifitwala_ed.api.calendar_subscription._subscription_window",
                return_value=(window_start, window_end),
            ),
            patch(
                "ifitwala_ed.api.calendar_subscription.calendar_staff_feed.get_staff_calendar_for_user",
                return_value={"events": []},
            ) as get_feed,
            patch(
                "ifitwala_ed.api.calendar_subscription.build_staff_calendar_ics",
                return_value="BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n",
            ),
        ):
            frappe.local.response = {}
            calendar_subscription.download_staff_calendar_subscription("token-value.ics")

        get_feed.assert_called_once_with(
            user="staff@example.com",
            from_datetime=window_start.isoformat(),
            to_datetime=window_end.isoformat(),
            sources=["student_group", "meeting", "school_event", "staff_holiday"],
            force_refresh=False,
        )
        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")
        self.assertEqual(frappe.local.response.get("content_type"), "text/calendar; charset=utf-8")
        self.assertEqual(frappe.local.response.get("filename"), "ifitwala-staff-calendar.ics")
        self.assertEqual(
            (frappe.local.response.get("headers") or {}).get("Cache-Control"),
            "private, max-age=300, must-revalidate",
        )

    def test_token_normalization_strips_route_suffix(self):
        self.assertEqual(calendar_subscription._normalize_token("/abc123.ics/"), "abc123")
