# ifitwala_ed/schedule/api/test_calendar.py

from datetime import datetime, time, timedelta
from unittest import TestCase
from unittest.mock import patch

import frappe
import pytz

from ifitwala_ed.schedule.api.calendar import details as calendar_details
from ifitwala_ed.schedule.api.calendar.core import (
    CAL_MIN_DURATION,
    _attach_duration,
    _coerce_time,
    _student_group_memberships,
    _system_tzinfo,
    _time_to_str,
)
from ifitwala_ed.schedule.api.calendar.details import _resolve_sg_schedule_context
from ifitwala_ed.schedule.api.calendar.staff_feed import _collect_meeting_events


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

    def get(self, key, default=None):
        return getattr(self, key, default)


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

    def test_collect_meeting_events_falls_back_to_school_default_color(self):
        tzinfo = _system_tzinfo()
        window_start = datetime(2026, 2, 1, 0, 0, 0)
        window_end = datetime(2026, 2, 7, 0, 0, 0)
        meeting_row = frappe._dict(
            {
                "name": "MTG-0001",
                "meeting_name": "Weekly Check-in",
                "date": "2026-02-02",
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "from_datetime": "2026-02-02 09:00:00",
                "to_datetime": "2026-02-02 10:00:00",
                "location": None,
                "school": "SCHOOL-1",
                "team": None,
                "virtual_meeting_link": None,
            }
        )

        def _fake_get_all(doctype, filters=None, fields=None, ignore_permissions=False, **kwargs):
            if doctype == "School":
                return [frappe._dict({"name": "SCHOOL-1", "meeting_color": "#a4f3dd"})]
            if doctype == "Team":
                return []
            raise AssertionError(f"Unexpected get_all call: doctype={doctype!r}")

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.staff_feed._resolve_employee_for_user",
                return_value={"name": "EMP-0001"},
            ),
            patch("ifitwala_ed.schedule.api.calendar.staff_feed.frappe.db.sql", return_value=[meeting_row]),
            patch("ifitwala_ed.schedule.api.calendar.staff_feed.frappe.get_all", side_effect=_fake_get_all),
        ):
            events = _collect_meeting_events("staff@example.com", window_start, window_end, tzinfo)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].color, "#a4f3dd")

    def test_collect_meeting_events_keeps_explicit_team_color_over_school_default(self):
        tzinfo = _system_tzinfo()
        window_start = datetime(2026, 2, 1, 0, 0, 0)
        window_end = datetime(2026, 2, 7, 0, 0, 0)
        meeting_row = frappe._dict(
            {
                "name": "MTG-0002",
                "meeting_name": "Leadership Sync",
                "date": "2026-02-03",
                "start_time": "11:00:00",
                "end_time": "12:00:00",
                "from_datetime": "2026-02-03 11:00:00",
                "to_datetime": "2026-02-03 12:00:00",
                "location": None,
                "school": "SCHOOL-1",
                "team": "TEAM-1",
                "virtual_meeting_link": None,
            }
        )

        def _fake_get_all(doctype, filters=None, fields=None, ignore_permissions=False, **kwargs):
            if doctype == "Team":
                return [frappe._dict({"name": "TEAM-1", "meeting_color": "#112233", "school": "SCHOOL-1"})]
            if doctype == "School":
                return [frappe._dict({"name": "SCHOOL-1", "meeting_color": "#a4f3dd"})]
            raise AssertionError(f"Unexpected get_all call: doctype={doctype!r}")

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.staff_feed._resolve_employee_for_user",
                return_value={"name": "EMP-0001"},
            ),
            patch("ifitwala_ed.schedule.api.calendar.staff_feed.frappe.db.sql", return_value=[meeting_row]),
            patch("ifitwala_ed.schedule.api.calendar.staff_feed.frappe.get_all", side_effect=_fake_get_all),
        ):
            events = _collect_meeting_events("staff@example.com", window_start, window_end, tzinfo)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].color, "#112233")

    def test_get_school_event_details_tolerates_missing_event_type_field(self):
        doc = _FakeDoc(
            {
                "subject": "Assembly",
                "school": "SCHOOL-1",
                "location": "Hall",
                "event_category": "Other",
                "all_day": 0,
                "color": None,
                "description": "<p>Bring your planner.</p>",
                "starts_on": "2026-04-10 08:00:00",
                "ends_on": "2026-04-10 09:00:00",
                "reference_type": None,
                "reference_name": None,
                "docstatus": 0,
            },
            "SE-0001",
        )

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.details.frappe.session",
                frappe._dict({"user": "teacher@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.details.frappe.get_doc", return_value=doc),
            patch("ifitwala_ed.schedule.api.calendar.details._school_event_access_allowed", return_value=True),
            patch(
                "ifitwala_ed.schedule.api.calendar.details._system_tzinfo",
                return_value=pytz.timezone("Asia/Bangkok"),
            ),
        ):
            payload = calendar_details.get_school_event_details("SE-0001")

        self.assertEqual(payload["name"], "SE-0001")
        self.assertEqual(payload["subject"], "Assembly")
        self.assertEqual(payload["event_category"], "Other")
        self.assertIsNone(payload["event_type"])
        self.assertEqual(payload["timezone"], "Asia/Bangkok")

    def test_school_event_access_blocks_staff_for_guardian_only_ancestor_event(self):
        doc = _FakeDoc(
            {
                "subject": "Parent Workshop",
                "school": "ISS",
                "location": "Hall",
                "event_category": "Parent Engagement",
                "all_day": 0,
                "color": None,
                "description": "<p>Parents only.</p>",
                "starts_on": "2026-04-10 08:00:00",
                "ends_on": "2026-04-10 09:00:00",
                "reference_type": None,
                "reference_name": None,
                "docstatus": 0,
                "audience": [frappe._dict({"audience_type": "All Guardians", "team": None})],
                "participants": [],
            },
            "SE-0002",
        )

        with (
            patch("ifitwala_ed.schedule.api.calendar.details.frappe.get_roles", return_value=["Employee"]),
            patch(
                "ifitwala_ed.schedule.api.calendar.details._resolve_employee_for_user",
                return_value={"school": "IHS"},
            ),
            patch("ifitwala_ed.schedule.api.calendar.details.get_ancestor_schools", return_value=["IHS", "ISS"]),
            patch("ifitwala_ed.schedule.api.calendar.details.get_user_membership", return_value={"teams": set()}),
        ):
            allowed = calendar_details._school_event_access_allowed(doc, "teacher@example.com")

        self.assertFalse(allowed)

    def test_school_event_access_allows_guardian_for_parent_school_event(self):
        doc = _FakeDoc(
            {
                "subject": "Parent Workshop",
                "school": "ISS",
                "location": "Hall",
                "event_category": "Parent Engagement",
                "all_day": 0,
                "color": None,
                "description": "<p>Parents only.</p>",
                "starts_on": "2026-04-10 08:00:00",
                "ends_on": "2026-04-10 09:00:00",
                "reference_type": None,
                "reference_name": None,
                "docstatus": 0,
                "audience": [
                    frappe._dict(
                        {
                            "audience_type": "All Guardians",
                            "student_group": None,
                            "include_guardians": 0,
                            "include_students": 0,
                            "team": None,
                        }
                    )
                ],
                "participants": [],
            },
            "SE-0003",
        )
        context = {
            "user": "guardian@example.com",
            "children": [{"student": "STU-1", "full_name": "Amina Example", "school": "IHS"}],
            "child_by_student": {"STU-1": {"student": "STU-1", "full_name": "Amina Example", "school": "IHS"}},
            "student_names": ["STU-1"],
            "student_school_names": {"STU-1": {"IHS"}},
            "eligible_school_targets_by_student": {"STU-1": {"IHS", "ISS"}},
            "membership_by_student": {"STU-1": set()},
        }

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.details.frappe.session",
                frappe._dict({"user": "guardian@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.details.frappe.get_roles", return_value=["Guardian"]),
            patch(
                "ifitwala_ed.schedule.api.calendar.details._resolve_guardian_communication_context",
                return_value=context,
            ),
        ):
            allowed = calendar_details._school_event_access_allowed(doc, "guardian@example.com")

        self.assertTrue(allowed)

    def test_get_student_group_event_details_includes_task_creation_context(self):
        tzinfo = pytz.timezone("Asia/Bangkok")
        event_start = datetime(2026, 4, 22, 8, 0, 0)
        event_end = datetime(2026, 4, 22, 9, 0, 0)

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.details.frappe.session",
                frappe._dict({"user": "teacher@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.details._system_tzinfo", return_value=tzinfo),
            patch(
                "ifitwala_ed.schedule.api.calendar.details._resolve_sg_schedule_context",
                return_value={
                    "student_group": "GROUP-1",
                    "rotation_day": 2,
                    "block_number": 3,
                    "block_label": "Block 3",
                    "session_date": "2026-04-22",
                    "location": "Room 5",
                    "location_missing_reason": None,
                    "start": event_start,
                    "end": event_end,
                },
            ),
            patch("ifitwala_ed.schedule.api.calendar.details._user_has_student_group_access", return_value=True),
            patch(
                "ifitwala_ed.schedule.api.calendar.details.frappe.db.get_value",
                return_value=frappe._dict(
                    {
                        "name": "GROUP-1",
                        "student_group_name": "Biology A",
                        "group_based_on": "Course",
                        "program": "IB",
                        "course": "COURSE-1",
                        "cohort": "G6",
                        "school": "SCHOOL-1",
                    }
                ),
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.details._course_meta_map",
                return_value={"COURSE-1": {"course_name": "Biology"}},
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.details.planning.resolve_active_class_teaching_plan",
                return_value={
                    "status": "ready",
                    "class_teaching_plan": "CLASS-PLAN-1",
                    "active_plan_count": 1,
                },
            ),
        ):
            payload = calendar_details.get_student_group_event_details("sg::GROUP-1::2026-04-22T08:00:00")

        self.assertEqual(payload["student_group"], "GROUP-1")
        self.assertEqual(payload["course_name"], "Biology")
        self.assertEqual(
            payload["task_creation"],
            {
                "status": "ready",
                "class_teaching_plan": "CLASS-PLAN-1",
            },
        )

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

        with patch("ifitwala_ed.schedule.api.calendar.core.frappe.get_all", side_effect=_fake_get_all):
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
