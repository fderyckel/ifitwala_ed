# ifitwala_ed/api/test_student_calendar.py

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import frappe
import pytz

from ifitwala_ed.api.calendar_core import CalendarEvent
from ifitwala_ed.api.student_calendar import (
    STUDENT_CALENDAR_INVALIDATE_EVENT,
    get_student_calendar,
    invalidate_student_calendar_cache,
    refresh_student_calendar_views,
)


class _DummyCache:
    def __init__(self):
        self.store: dict[str, object] = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value

    def delete_value(self, key):
        self.store.pop(key, None)

    def get_keys(self, pattern):
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        return [key for key in self.store if key.startswith(prefix)]


class TestStudentCalendar(TestCase):
    def test_get_student_calendar_includes_meetings(self):
        tzinfo = pytz.timezone("Asia/Bangkok")
        cache = _DummyCache()
        window_start = tzinfo.localize(datetime(2026, 2, 1, 0, 0, 0))
        window_end = tzinfo.localize(datetime(2026, 2, 7, 0, 0, 0))
        meeting_event = CalendarEvent(
            id="meeting::MTG-0001",
            title="Guardian Meeting",
            start=tzinfo.localize(datetime(2026, 2, 2, 9, 0, 0)),
            end=tzinfo.localize(datetime(2026, 2, 2, 10, 0, 0)),
            source="meeting",
            color="#8b5cf6",
            all_day=False,
            meta={"location": "Room 101"},
        )

        with (
            patch("ifitwala_ed.api.student_calendar.frappe.session", frappe._dict({"user": "student@example.com"})),
            patch("ifitwala_ed.api.student_calendar.frappe.db.get_value", return_value="STU-0001"),
            patch("ifitwala_ed.api.student_calendar.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.student_calendar._system_tzinfo", return_value=tzinfo),
            patch("ifitwala_ed.api.student_calendar._resolve_window", return_value=(window_start, window_end)),
            patch("ifitwala_ed.api.student_calendar._get_student_enrolled_groups", return_value=[]),
            patch("ifitwala_ed.api.student_calendar._fetch_classes", return_value=[]),
            patch("ifitwala_ed.api.student_calendar._fetch_school_events", return_value=[]),
            patch(
                "ifitwala_ed.api.student_calendar._fetch_meetings",
                return_value=[meeting_event],
            ) as mocked_fetch_meetings,
            patch("ifitwala_ed.api.student_calendar.frappe.get_all", return_value=[]),
            patch("ifitwala_ed.api.student_calendar.now_datetime", return_value=datetime(2026, 2, 1, 8, 0, 0)),
        ):
            payload = get_student_calendar(force_refresh=True)

        self.assertEqual(len(payload.get("events", [])), 1)
        self.assertEqual(payload["events"][0]["source"], "meeting")
        mocked_fetch_meetings.assert_called_once_with(
            "student@example.com",
            "STU-0001",
            window_start,
            window_end,
            tzinfo,
        )

    def test_invalidate_student_calendar_cache_removes_all_windows_for_resolved_student(self):
        cache = _DummyCache()
        cache.store = {
            "ifw:stud-cal:STU-0001:2026-02-01:2026-02-07": {"events": []},
            "ifw:stud-cal:STU-0001:2026-02-08:2026-02-14": {"events": []},
            "ifw:stud-cal:STU-0002:2026-02-01:2026-02-07": {"events": []},
        }

        with (
            patch("ifitwala_ed.api.student_calendar.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.api.student_calendar.frappe.get_all",
                return_value=[frappe._dict({"name": "STU-0001"})],
            ),
        ):
            invalidate_student_calendar_cache(user="student@example.com")

        self.assertNotIn("ifw:stud-cal:STU-0001:2026-02-01:2026-02-07", cache.store)
        self.assertNotIn("ifw:stud-cal:STU-0001:2026-02-08:2026-02-14", cache.store)
        self.assertIn("ifw:stud-cal:STU-0002:2026-02-01:2026-02-07", cache.store)

    def test_refresh_student_calendar_views_invalidates_cache_and_publishes_realtime(self):
        cache = _DummyCache()
        cache.store = {
            "ifw:stud-cal:STU-0001:2026-02-01:2026-02-07": {"events": []},
            "ifw:stud-cal:STU-0002:2026-02-01:2026-02-07": {"events": []},
        }

        with (
            patch("ifitwala_ed.api.student_calendar.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.api.student_calendar.frappe.get_all",
                return_value=[
                    frappe._dict({"name": "STU-0001", "student_email": "student.one@example.com"}),
                    frappe._dict({"name": "STU-0002", "student_email": "student.two@example.com"}),
                ],
            ),
            patch("ifitwala_ed.api.student_calendar.frappe.publish_realtime") as mocked_publish,
        ):
            refresh_student_calendar_views(
                users=["student.one@example.com", "student.two@example.com"],
                source="meeting",
                source_name="MTG-0001",
            )

        self.assertFalse(cache.store)
        self.assertEqual(mocked_publish.call_count, 2)
        mocked_publish.assert_any_call(
            STUDENT_CALENDAR_INVALIDATE_EVENT,
            message={"source": "meeting", "source_name": "MTG-0001"},
            user="student.one@example.com",
            after_commit=True,
        )
        mocked_publish.assert_any_call(
            STUDENT_CALENDAR_INVALIDATE_EVENT,
            message={"source": "meeting", "source_name": "MTG-0001"},
            user="student.two@example.com",
            after_commit=True,
        )
