# ifitwala_ed/schedule/api/test_calendar_quick_create_availability.py

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.schedule.api.calendar import quick_create as calendar_quick_create


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


class TestCalendarQuickCreateAvailability(TestCase):
    def test_assert_students_available_for_meeting_blocks_busy_students(self):
        window_start = datetime(2026, 2, 1, 9, 0, 0)
        window_end = datetime(2026, 2, 1, 10, 0, 0)

        def _seed_busy(contexts, start, end, busy_by_user):
            busy_by_user["student@example.com"].append((window_start, window_end))

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._resolve_attendee_contexts",
                return_value=[
                    {
                        "user": "student@example.com",
                        "kind": "student",
                        "label": "Student Example",
                    }
                ],
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_student_busy_windows",
                side_effect=_seed_busy,
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_meeting_busy_windows"),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_school_event_busy_windows"),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_student_schedule_conflict_labels",
                return_value={"student@example.com": {"Class: Biology (Sun 1 Feb 2026 09:00 - 10:00)"}},
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_student_meeting_conflict_labels",
                return_value={},
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_student_school_event_conflict_labels",
                return_value={},
            ),
        ):
            with self.assertRaises(frappe.ValidationError) as exc:
                calendar_quick_create._assert_students_available_for_meeting(
                    attendees=[{"user": "student@example.com", "kind": "student"}],
                    organizer_user="staff@example.com",
                    window_start=window_start,
                    window_end=window_end,
                )

        self.assertIn("Student Example", str(exc.exception))
        self.assertIn("Class: Biology", str(exc.exception))

    def test_suggest_meeting_rooms_rechecks_location_booking_each_request(self):
        rooms = [
            frappe._dict(
                {
                    "name": "D201",
                    "location_name": "D201",
                    "parent_location": None,
                    "maximum_capacity": 20,
                    "location_type": None,
                    "location_type_name": None,
                    "is_group": 0,
                }
            ),
            frappe._dict(
                {
                    "name": "D204",
                    "location_name": "D204",
                    "parent_location": None,
                    "maximum_capacity": 20,
                    "location_type": None,
                    "location_type_name": None,
                    "is_group": 0,
                }
            ),
        ]
        conflict_rows = [
            [],
            [
                {
                    "source_doctype": "Student Group",
                    "source_name": "25-26-G6-Eng/IIS 2025-2026",
                    "location": "D201-Teaching Slot",
                    "from": datetime(2026, 5, 29, 10, 15, 0),
                    "to": datetime(2026, 5, 29, 11, 10, 0),
                }
            ],
        ]

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.rooms.frappe.has_permission", return_value=True),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms._ensure_allowed_school", return_value="SCHOOL-1"
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms._ensure_allowed_location_type", return_value=None
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms._ensure_allowed_location",
                side_effect=lambda user, school, location: location,
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms._room_rows_for_school_scope", return_value=rooms
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms.get_location_scope",
                side_effect=lambda room, include_children=True: (
                    [room, "D201-Teaching Slot"] if room == "D201" else [room]
                ),
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms.find_room_conflicts", side_effect=conflict_rows
            ),
        ):
            first = calendar_quick_create.suggest_meeting_rooms(
                school="SCHOOL-1",
                date="2026-05-29",
                start_time="10:15",
                end_time="10:35",
                capacity_needed=2,
                limit=8,
            )
            second = calendar_quick_create.suggest_meeting_rooms(
                school="SCHOOL-1",
                date="2026-05-29",
                start_time="10:15",
                end_time="10:35",
                selected_location="D201",
                capacity_needed=2,
                limit=8,
            )

        self.assertEqual([room["value"] for room in first["rooms"]], ["D201", "D204"])
        self.assertEqual([room["value"] for room in second["rooms"]], ["D204"])
        self.assertEqual(second["selected_location"], "D201")
        self.assertEqual(second["selected_location_available"], False)

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
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._", side_effect=lambda message: message),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability.frappe.has_permission", return_value=True
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._resolve_attendee_contexts",
                return_value=[
                    {
                        "user": "student@example.com",
                        "label": "Student Example",
                        "kind": "student",
                        "availability_mode": "school_schedule",
                    }
                ],
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_employee_busy_windows"),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_student_busy_windows"),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_meeting_busy_windows"),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_school_event_busy_windows"),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._ensure_allowed_school",
                return_value="SCHOOL-1",
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._ensure_allowed_location_type",
                return_value="Hall",
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms._room_rows_for_school_scope",
                return_value=room_rows,
            ) as mocked_room_scope,
            patch("ifitwala_ed.schedule.api.calendar.quick_create.rooms._collect_room_busy_windows", return_value={}),
        ):
            payload = calendar_quick_create.suggest_meeting_slots(
                attendees=[{"user": "student@example.com", "kind": "student"}],
                duration_minutes=60,
                date_from="2026-02-01",
                date_to="2026-02-01",
                day_start_time="08:00",
                day_end_time="09:00",
                school="SCHOOL-1",
                location_type="Hall",
                require_room=True,
            )

        mocked_room_scope.assert_called_once_with(
            "SCHOOL-1",
            2,
            location_type="Hall",
        )
        self.assertEqual(len(payload["slots"]), 1)
        self.assertEqual(payload["slots"][0]["suggested_room"]["value"], "ROOM-1")
        self.assertEqual(payload["slots"][0]["available_room_count"], 2)
        self.assertIn(
            "Exact matches already include at least one free room in the selected school scope.",
            payload["notes"],
        )
        self.assertIn("Room ranking is limited to location type Hall.", payload["notes"])

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
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._", side_effect=lambda message: message),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability.frappe.has_permission", return_value=True
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._resolve_attendee_contexts",
                return_value=[
                    {
                        "user": "student@example.com",
                        "label": "Student Example",
                        "kind": "student",
                        "availability_mode": "school_schedule",
                    }
                ],
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_employee_busy_windows"),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_student_busy_windows"),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_meeting_busy_windows"),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.availability._collect_school_event_busy_windows"),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._ensure_allowed_school",
                return_value="SCHOOL-1",
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.availability._ensure_allowed_location_type",
                return_value="Hall",
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms._room_rows_for_school_scope",
                return_value=room_rows,
            ) as mocked_room_scope,
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.rooms._collect_room_busy_windows",
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
                location_type="Hall",
                require_room=True,
            )

        mocked_room_scope.assert_called_once_with(
            "SCHOOL-1",
            2,
            location_type="Hall",
        )
        self.assertEqual(payload["slots"], [])
        self.assertEqual(payload["fallback_slots"], [])
        self.assertIn("excluded because no room was free", payload["notes"][-1])
