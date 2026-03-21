# ifitwala_ed/api/test_calendar.py

from datetime import datetime, time, timedelta
from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import calendar_quick_create
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
    get_meeting_team_attendees,
    search_meeting_attendees,
    suggest_meeting_rooms,
    suggest_meeting_slots,
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
        user_rows = {
            "staff@example.com": frappe._dict({"name": "staff@example.com", "full_name": "Staff Example"}),
            "student@example.com": frappe._dict({"name": "student@example.com", "full_name": "Student Example"}),
        }

        def _fake_get_doc(*args, **kwargs):
            if len(args) == 1 and isinstance(args[0], dict):
                payload = args[0]
                captured_payloads.append(payload)
                return _FakeDoc(payload, "MTG-TEST-0001")
            if args == ("System Settings", "System Settings"):
                return frappe._dict({"time_zone": "Asia/Bangkok"})
            raise AssertionError(f"Unexpected get_doc call: args={args!r} kwargs={kwargs!r}")

        def _fake_get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype == "Employee":
                return []
            if doctype == "User":
                requested = (filters or {}).get("name", [None, []])[1] or []
                return [user_rows[name] for name in requested if name in user_rows]
            raise AssertionError(f"Unexpected get_all call: doctype={doctype!r}")

        with (
            patch("ifitwala_ed.api.calendar_quick_create.frappe.session", frappe._dict({"user": "staff@example.com"})),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.get_doc", side_effect=_fake_get_doc),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.get_all", side_effect=_fake_get_all),
            patch(
                "ifitwala_ed.api.calendar_quick_create._get_quick_create_scope",
                return_value={
                    "base_school": "SCHOOL-1",
                    "school_scope": ["SCHOOL-1"],
                    "student_scope": ["SCHOOL-1"],
                    "is_admin_like": False,
                },
            ),
        ):
            first = create_meeting_quick(
                client_request_id="req-1",
                meeting_name="Weekly Check-in",
                date="2026-02-01",
                start_time="09:00",
                end_time="10:00",
                school="SCHOOL-1",
                participants=[{"user": "student@example.com", "kind": "student", "label": "Student Example"}],
            )
            second = create_meeting_quick(
                client_request_id="req-1",
                meeting_name="Weekly Check-in",
                date="2026-02-01",
                start_time="09:00",
                end_time="10:00",
                school="SCHOOL-1",
                participants=[{"user": "student@example.com", "kind": "student", "label": "Student Example"}],
            )

        self.assertEqual(first.get("status"), "created")
        self.assertEqual(second.get("status"), "already_processed")
        self.assertEqual(second.get("idempotent"), True)
        self.assertEqual(len(captured_payloads), 1)
        self.assertEqual(captured_payloads[0].get("school"), "SCHOOL-1")
        self.assertEqual(captured_payloads[0].get("visibility_scope"), "Participants Only")
        self.assertEqual(
            captured_payloads[0].get("participants"),
            [
                {"participant": "student@example.com", "participant_name": "Student Example"},
                {"participant": "staff@example.com", "participant_name": "Staff Example"},
            ],
        )

    def test_create_school_event_quick_defaults_custom_users_to_session_user(self):
        cache = _DummyCache()
        captured_payloads = []

        def _fake_get_doc(*args, **kwargs):
            if len(args) == 1 and isinstance(args[0], dict):
                payload = args[0]
                captured_payloads.append(payload)
                return _FakeDoc(payload, "SEVENT-2026-000001")
            if args == ("System Settings", "System Settings"):
                return frappe._dict({"time_zone": "Asia/Bangkok"})
            raise AssertionError(f"Unexpected get_doc call: args={args!r} kwargs={kwargs!r}")

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

    def test_search_meeting_attendees_facade_delegates_new_contract(self):
        expected = {"results": [{"value": "student@example.com"}], "notes": ["note"]}

        with patch("ifitwala_ed.api.calendar._search_meeting_attendees", return_value=expected) as mocked:
            payload = search_meeting_attendees(
                query="stu",
                attendee_kinds=["employee", "student"],
                limit=6,
            )

        mocked.assert_called_once_with(
            query="stu",
            attendee_kinds=["employee", "student"],
            limit=6,
        )
        self.assertEqual(payload, expected)

    def test_get_meeting_team_attendees_facade_delegates_new_contract(self):
        expected = {"team": "TEAM-1", "results": [{"value": "staff@example.com"}]}

        with patch("ifitwala_ed.api.calendar._get_meeting_team_attendees", return_value=expected) as mocked:
            payload = get_meeting_team_attendees(team="TEAM-1")

        mocked.assert_called_once_with(team="TEAM-1")
        self.assertEqual(payload, expected)

    def test_suggest_meeting_slots_facade_delegates_new_contract(self):
        expected = {
            "slots": [
                {
                    "start": "2026-02-01T09:00:00",
                    "available_room_count": 2,
                    "suggested_room": {"value": "ROOM-1", "label": "Room 1"},
                }
            ],
            "fallback_slots": [],
            "notes": [],
            "duration_minutes": 45,
            "attendees": [],
        }

        with patch("ifitwala_ed.api.calendar._suggest_meeting_slots", return_value=expected) as mocked:
            payload = suggest_meeting_slots(
                attendees=[{"user": "student@example.com", "kind": "student"}],
                duration_minutes=45,
                date_from="2026-02-01",
                date_to="2026-02-05",
                day_start_time="08:00",
                day_end_time="17:00",
                school="SCHOOL-1",
                require_room=True,
            )

        mocked.assert_called_once_with(
            attendees=[{"user": "student@example.com", "kind": "student"}],
            duration_minutes=45,
            date_from="2026-02-01",
            date_to="2026-02-05",
            day_start_time="08:00",
            day_end_time="17:00",
            school="SCHOOL-1",
            require_room=True,
        )
        self.assertEqual(payload, expected)

    def test_suggest_meeting_rooms_facade_delegates_new_contract(self):
        expected = {"rooms": [{"value": "ROOM-1"}], "notes": []}

        with patch("ifitwala_ed.api.calendar._suggest_meeting_rooms", return_value=expected) as mocked:
            payload = suggest_meeting_rooms(
                school="SCHOOL-1",
                date="2026-02-01",
                start_time="09:00",
                end_time="10:00",
                capacity_needed=4,
                limit=5,
            )

        mocked.assert_called_once_with(
            school="SCHOOL-1",
            date="2026-02-01",
            start_time="09:00",
            end_time="10:00",
            capacity_needed=4,
            limit=5,
        )
        self.assertEqual(payload, expected)

    def test_quick_create_slot_suggestions_include_best_room_when_required(self):
        cache = _DummyCache()
        room_rows = [
            frappe._dict(
                {
                    "name": "ROOM-1",
                    "location_name": "Room 1",
                    "parent_location": "Block A",
                    "maximum_capacity": 2,
                }
            ),
            frappe._dict(
                {
                    "name": "ROOM-2",
                    "location_name": "Room 2",
                    "parent_location": "Block B",
                    "maximum_capacity": 8,
                }
            ),
        ]

        with (
            patch("ifitwala_ed.api.calendar_quick_create.frappe.session", frappe._dict({"user": "staff@example.com"})),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.api.calendar_quick_create._resolve_attendee_contexts",
                return_value=[
                    {
                        "user": "student@example.com",
                        "label": "Student Example",
                        "kind": "student",
                        "availability_mode": "school_schedule",
                    }
                ],
            ),
            patch("ifitwala_ed.api.calendar_quick_create._collect_employee_busy_windows"),
            patch("ifitwala_ed.api.calendar_quick_create._collect_student_busy_windows"),
            patch("ifitwala_ed.api.calendar_quick_create._collect_meeting_busy_windows"),
            patch("ifitwala_ed.api.calendar_quick_create._collect_school_event_busy_windows"),
            patch("ifitwala_ed.api.calendar_quick_create._ensure_allowed_school", return_value="SCHOOL-1"),
            patch("ifitwala_ed.api.calendar_quick_create._room_rows_for_school_scope", return_value=room_rows),
            patch("ifitwala_ed.api.calendar_quick_create._collect_room_busy_windows", return_value={}),
        ):
            payload = calendar_quick_create.suggest_meeting_slots(
                attendees=[{"user": "student@example.com", "kind": "student"}],
                duration_minutes=60,
                date_from="2026-02-01",
                date_to="2026-02-01",
                day_start_time="08:00",
                day_end_time="09:00",
                school="SCHOOL-1",
                require_room=True,
            )

        self.assertEqual(len(payload["slots"]), 1)
        self.assertEqual(payload["slots"][0]["suggested_room"]["value"], "ROOM-1")
        self.assertEqual(payload["slots"][0]["available_room_count"], 2)
        self.assertIn(
            "Exact matches already include at least one free room in the selected school scope.",
            payload["notes"],
        )

    def test_quick_create_slot_suggestions_drop_exact_match_without_free_room(self):
        cache = _DummyCache()
        room_rows = [
            frappe._dict(
                {
                    "name": "ROOM-1",
                    "location_name": "Room 1",
                    "parent_location": "Block A",
                    "maximum_capacity": 2,
                }
            )
        ]
        blocked_window = (
            datetime(2026, 2, 1, 8, 0, 0),
            datetime(2026, 2, 1, 9, 0, 0),
        )

        with (
            patch("ifitwala_ed.api.calendar_quick_create.frappe.session", frappe._dict({"user": "staff@example.com"})),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.api.calendar_quick_create.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.api.calendar_quick_create._resolve_attendee_contexts",
                return_value=[
                    {
                        "user": "student@example.com",
                        "label": "Student Example",
                        "kind": "student",
                        "availability_mode": "school_schedule",
                    }
                ],
            ),
            patch("ifitwala_ed.api.calendar_quick_create._collect_employee_busy_windows"),
            patch("ifitwala_ed.api.calendar_quick_create._collect_student_busy_windows"),
            patch("ifitwala_ed.api.calendar_quick_create._collect_meeting_busy_windows"),
            patch("ifitwala_ed.api.calendar_quick_create._collect_school_event_busy_windows"),
            patch("ifitwala_ed.api.calendar_quick_create._ensure_allowed_school", return_value="SCHOOL-1"),
            patch("ifitwala_ed.api.calendar_quick_create._room_rows_for_school_scope", return_value=room_rows),
            patch(
                "ifitwala_ed.api.calendar_quick_create._collect_room_busy_windows",
                return_value={"ROOM-1": [blocked_window]},
            ),
        ):
            payload = calendar_quick_create.suggest_meeting_slots(
                attendees=[{"user": "student@example.com", "kind": "student"}],
                duration_minutes=60,
                date_from="2026-02-01",
                date_to="2026-02-01",
                day_start_time="08:00",
                day_end_time="09:00",
                school="SCHOOL-1",
                require_room=True,
            )

        self.assertEqual(payload["slots"], [])
        self.assertEqual(payload["fallback_slots"], [])
        self.assertIn("excluded because no room was free", payload["notes"][-1])
