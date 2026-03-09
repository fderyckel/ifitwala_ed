# ifitwala_ed/api/test_calendar.py

from datetime import datetime, time, timedelta
from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api.calendar import (
    CAL_MIN_DURATION,
    _attach_duration,
    _coerce_time,
    _resolve_sg_schedule_context,
    _student_group_memberships,
    _system_tzinfo,
    _time_to_str,
    create_meeting_quick,
    create_school_event_quick,
)


class _DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyCache:
    def __init__(self):
        self.store: dict[str, str] = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value

    def lock(self, key, timeout=15):
        return _DummyLock()


class _FakeDoc:
    def __init__(self, payload: dict, name: str):
        self.name = name
        for key, value in payload.items():
            setattr(self, key, value)

        if payload.get("meeting_name"):
            self.meeting_name = payload.get("meeting_name")
            self.from_datetime = f"{payload.get('date')} {payload.get('start_time')}:00"
            self.to_datetime = f"{payload.get('date')} {payload.get('end_time')}:00"

        if payload.get("subject"):
            self.subject = payload.get("subject")
            self.starts_on = payload.get("starts_on")
            self.ends_on = payload.get("ends_on")

    def insert(self):
        return self


class TestCalendarApi(TestCase):
    def test_coerce_time_supports_multiple_input_types(self):
        self.assertEqual(_coerce_time(time(9, 15, 0)), time(9, 15, 0))
        self.assertEqual(_coerce_time(datetime(2026, 2, 1, 11, 0, 0)), time(11, 0, 0))
        self.assertEqual(_coerce_time(timedelta(hours=3, minutes=5)), time(3, 5, 0))
        self.assertIsNone(_coerce_time("not-a-time"))

    def test_time_to_str_normalizes_values(self):
        self.assertEqual(_time_to_str(time(8, 0, 1)), "08:00:01")
        self.assertEqual(_time_to_str(timedelta(hours=1, minutes=2, seconds=3)), "01:02:03")
        self.assertEqual(_time_to_str(b"12:34:56"), "12:34:56")

    def test_attach_duration_enforces_minimum_duration(self):
        start_dt = datetime(2026, 2, 1, 10, 0, 0)
        self.assertEqual(_attach_duration(start_dt, None), CAL_MIN_DURATION)
        self.assertEqual(_attach_duration(start_dt, datetime(2026, 2, 1, 9, 0, 0)), CAL_MIN_DURATION)
        self.assertEqual(_attach_duration(start_dt, datetime(2026, 2, 1, 11, 30, 0)), timedelta(hours=1, minutes=30))

    def test_resolve_sg_schedule_context_supports_legacy_event_id(self):
        tzinfo = _system_tzinfo()
        context = _resolve_sg_schedule_context("sg::SG-TEST::2026-02-01T10:00:00", tzinfo)
        self.assertEqual(context["student_group"], "SG-TEST")
        self.assertIsNone(context["rotation_day"])
        self.assertIsNone(context["block_number"])
        self.assertEqual(context["session_date"], "2026-02-01")
        self.assertEqual(context["end"] - context["start"], CAL_MIN_DURATION)

    def test_create_meeting_quick_is_idempotent(self):
        cache = _DummyCache()
        captured_payloads = []

        def _fake_get_doc(payload):
            captured_payloads.append(payload)
            return _FakeDoc(payload, "MTG-TEST-0001")

        with (
            patch("ifitwala_ed.api.calendar_quick_create.frappe.session", frappe._dict({"user": "staff@example.com"})),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.get_doc", side_effect=_fake_get_doc),
        ):
            first = create_meeting_quick(
                client_request_id="req-1",
                meeting_name="Weekly Check-in",
                date="2026-02-01",
                start_time="09:00",
                end_time="10:00",
            )
            second = create_meeting_quick(
                client_request_id="req-1",
                meeting_name="Weekly Check-in",
                date="2026-02-01",
                start_time="09:00",
                end_time="10:00",
            )

        self.assertEqual(first.get("status"), "created")
        self.assertEqual(second.get("status"), "already_processed")
        self.assertEqual(second.get("idempotent"), True)
        self.assertEqual(len(captured_payloads), 1)
        self.assertEqual(captured_payloads[0].get("participants"), [{"participant": "staff@example.com"}])

    def test_create_school_event_quick_defaults_custom_users_to_session_user(self):
        cache = _DummyCache()
        captured_payloads = []

        def _fake_get_doc(payload):
            captured_payloads.append(payload)
            return _FakeDoc(payload, "SEVENT-2026-000001")

        with (
            patch("ifitwala_ed.api.calendar_quick_create.frappe.session", frappe._dict({"user": "staff@example.com"})),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.get_doc", side_effect=_fake_get_doc),
        ):
            response = create_school_event_quick(
                client_request_id="req-custom-1",
                subject="Parent Coffee Morning",
                school="SCHOOL-1",
                starts_on="2026-02-01T09:00",
                ends_on="2026-02-01T10:00",
                audience_type="Custom Users",
                event_category="Other",
            )

        self.assertEqual(response.get("status"), "created")
        self.assertEqual(len(captured_payloads), 1)
        self.assertEqual(captured_payloads[0].get("participants"), [{"participant": "staff@example.com"}])

    def test_student_group_memberships_does_not_filter_child_rows_by_active(self):
        observed_filters = []

        def _fake_get_all(doctype, filters=None, fields=None, ignore_permissions=False, **kwargs):
            self.assertEqual(doctype, "Student Group Instructor")
            observed_filters.append(dict(filters or {}))

            if filters.get("user_id") == "staff@example.com":
                return [frappe._dict({"parent": "SG-USER", "user_id": "staff@example.com"})]
            if filters.get("employee") == "EMP-0001":
                return [frappe._dict({"parent": "SG-EMP", "user_id": "assistant@example.com"})]
            if "instructor" in (filters or {}):
                return [frappe._dict({"parent": "SG-INS", "user_id": None})]
            return []

        with patch("ifitwala_ed.api.calendar_core.frappe.get_all", side_effect=_fake_get_all):
            group_names, instructor_ids = _student_group_memberships(
                user="staff@example.com",
                employee_id="EMP-0001",
                instructor_ids={"INS-0001"},
            )

        self.assertEqual(group_names, {"SG-USER", "SG-EMP", "SG-INS"})
        self.assertIn("INS-0001", instructor_ids)
        self.assertIn("assistant@example.com", instructor_ids)

        self.assertEqual(len(observed_filters), 3)
        for filters in observed_filters:
            self.assertEqual(filters.get("parenttype"), "Student Group")
            self.assertNotIn("active", filters)
