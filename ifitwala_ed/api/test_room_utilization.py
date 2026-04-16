# ifitwala_ed/api/test_room_utilization.py

from datetime import date
from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import room_utilization


class TestRoomUtilizationApi(TestCase):
    def test_get_room_utilization_filter_meta_includes_school_time_defaults(self):
        school_rows = [frappe._dict({"name": "ISS", "label": "Ifitwala Secondary School"})]
        lineage_school_rows = [
            frappe._dict(
                {
                    "name": "ISS",
                    "portal_calendar_start_time": "08:15:00",
                    "portal_calendar_end_time": "15:45:00",
                }
            )
        ]

        def mocked_get_all(doctype, *args, **kwargs):
            if doctype == "School" and kwargs.get("fields") == ["name", "school_name as label"]:
                return school_rows
            if doctype == "School" and kwargs.get("fields") == [
                "name",
                "portal_calendar_start_time",
                "portal_calendar_end_time",
            ]:
                return lineage_school_rows
            return []

        with (
            patch("ifitwala_ed.api.room_utilization.get_authorized_schools", return_value=["ISS"]),
            patch("ifitwala_ed.api.room_utilization.get_school_lineage", return_value=["ISS"]),
            patch("ifitwala_ed.api.room_utilization.frappe.get_all", side_effect=mocked_get_all),
            patch("ifitwala_ed.api.room_utilization._get_schedulable_location_type_options", return_value=[]),
        ):
            payload = room_utilization.get_room_utilization_filter_meta()

        self.assertEqual(payload["default_school"], "ISS")
        self.assertEqual(
            payload["time_util_defaults_by_school"]["ISS"],
            {
                "day_start_time": "08:15:00",
                "day_end_time": "15:45:00",
            },
        )

    def test_get_free_rooms_passes_location_type_to_visible_scope_helper(self):
        room_rows = [
            frappe._dict(
                {
                    "name": "EVENT-HALL",
                    "location_name": "Event Hall",
                    "parent_location": "Shared Building",
                    "maximum_capacity": 120,
                    "location_type": "Hall",
                    "location_type_name": "Hall",
                }
            )
        ]

        with (
            patch("ifitwala_ed.api.room_utilization._ensure_allowed_school", return_value="ISS"),
            patch("ifitwala_ed.api.room_utilization._require_location_booking_table"),
            patch(
                "ifitwala_ed.api.room_utilization.get_visible_location_rows_for_school",
                return_value=room_rows,
            ) as mocked_visible_rows,
            patch("ifitwala_ed.api.room_utilization.find_room_conflicts", return_value=[]),
        ):
            payload = room_utilization.get_free_rooms(
                filters={
                    "school": "ISS",
                    "date": "2026-02-01",
                    "start_time": "09:00",
                    "end_time": "10:00",
                    "location_type": "Hall",
                }
            )

        mocked_visible_rows.assert_called_once_with(
            "ISS",
            include_groups=False,
            only_schedulable=True,
            within_location=None,
            location_types=["Hall"],
            capacity_needed=None,
            fields=[
                "name",
                "location_name",
                "parent_location",
                "maximum_capacity",
                "location_type",
                "is_group",
            ],
            order_by="location_name asc",
            limit=800,
        )
        self.assertEqual(payload["rooms"][0]["room"], "EVENT-HALL")
        self.assertEqual(payload["rooms"][0]["location_type_name"], "Hall")

    def test_get_location_calendar_uses_group_scope_and_redacts_source_titles(self):
        location_rows = [
            frappe._dict(
                {
                    "name": "SHARED-BUILDING",
                    "location_name": "Shared Building",
                    "parent_location": None,
                    "location_type": None,
                    "location_type_name": None,
                    "is_group": 1,
                }
            ),
            frappe._dict(
                {
                    "name": "EVENT-HALL",
                    "location_name": "Event Hall",
                    "parent_location": "Shared Building",
                    "location_type": "Hall",
                    "location_type_name": "Hall",
                    "is_group": 0,
                }
            ),
        ]
        booking_rows = [
            frappe._dict(
                {
                    "name": "LB-0001",
                    "location": "EVENT-HALL",
                    "from_datetime": "2026-02-01 09:00:00",
                    "to_datetime": "2026-02-01 10:30:00",
                    "occupancy_type": "Meeting",
                    "source_doctype": "Meeting",
                    "source_name": "MTG-0001",
                }
            )
        ]

        with (
            patch("ifitwala_ed.api.room_utilization._ensure_allowed_school", return_value="ISS"),
            patch(
                "ifitwala_ed.api.room_utilization._validate_date_range",
                return_value=(date(2026, 2, 1), date(2026, 2, 2), 2),
            ),
            patch(
                "ifitwala_ed.api.room_utilization.get_visible_location_rows_for_school",
                return_value=location_rows,
            ),
            patch(
                "ifitwala_ed.api.room_utilization.get_location_scope",
                return_value=["SHARED-BUILDING", "EVENT-HALL"],
            ),
            patch("ifitwala_ed.api.room_utilization._require_location_booking_table"),
            patch("ifitwala_ed.api.room_utilization.frappe.db.has_column", return_value=True),
            patch("ifitwala_ed.api.room_utilization.frappe.get_all", return_value=booking_rows) as mocked_get_all,
        ):
            payload = room_utilization.get_location_calendar(
                filters={
                    "school": "ISS",
                    "from_date": "2026-02-01",
                    "to_date": "2026-02-02",
                    "location": "SHARED-BUILDING",
                }
            )

        self.assertEqual(payload["selected_location"], "SHARED-BUILDING")
        self.assertEqual(payload["selected_location_label"], "Shared Building")
        self.assertEqual(payload["note"], "Showing bookings for the selected location and all descendant spaces.")
        self.assertEqual(payload["events"][0]["title"], "Meeting · Event Hall")
        self.assertEqual(payload["events"][0]["meta"]["location_label"], "Event Hall")
        mocked_get_all.assert_called_once()
        self.assertEqual(
            mocked_get_all.call_args.kwargs["filters"]["location"],
            ["in", ("SHARED-BUILDING", "EVENT-HALL")],
        )

    def test_get_location_calendar_adds_student_group_and_course_for_teaching(self):
        location_rows = [
            frappe._dict(
                {
                    "name": "SCI-LAB",
                    "location_name": "Science Lab",
                    "parent_location": "Science Building",
                    "location_type": "Lab",
                    "location_type_name": "Lab",
                    "is_group": 0,
                }
            )
        ]
        booking_rows = [
            frappe._dict(
                {
                    "name": "LB-0100",
                    "location": "SCI-LAB",
                    "from_datetime": "2026-02-01 09:00:00",
                    "to_datetime": "2026-02-01 10:00:00",
                    "occupancy_type": "Teaching",
                    "source_doctype": "Student Group",
                    "source_name": "SG-8A-BIO",
                }
            )
        ]
        student_group_rows = [
            frappe._dict(
                {
                    "name": "SG-8A-BIO",
                    "student_group_name": "Grade 8A",
                    "course": "BIO-101",
                }
            )
        ]
        course_rows = [
            frappe._dict(
                {
                    "name": "BIO-101",
                    "course_name": "Biology",
                }
            )
        ]

        def mocked_get_all(doctype, *args, **kwargs):
            if doctype == "Location Booking":
                return booking_rows
            return []

        def mocked_db_get_all(doctype, *args, **kwargs):
            if doctype == "Student Group":
                return student_group_rows
            if doctype == "Course":
                return course_rows
            return []

        with (
            patch("ifitwala_ed.api.room_utilization._ensure_allowed_school", return_value="ISS"),
            patch(
                "ifitwala_ed.api.room_utilization._validate_date_range",
                return_value=(date(2026, 2, 1), date(2026, 2, 1), 1),
            ),
            patch(
                "ifitwala_ed.api.room_utilization.get_visible_location_rows_for_school",
                return_value=location_rows,
            ),
            patch(
                "ifitwala_ed.api.room_utilization.get_location_scope",
                return_value=["SCI-LAB"],
            ),
            patch("ifitwala_ed.api.room_utilization._require_location_booking_table"),
            patch("ifitwala_ed.api.room_utilization.frappe.db.has_column", return_value=True),
            patch("ifitwala_ed.api.room_utilization.frappe.get_all", side_effect=mocked_get_all),
            patch("ifitwala_ed.api.room_utilization.frappe.db.get_all", side_effect=mocked_db_get_all),
        ):
            payload = room_utilization.get_location_calendar(
                filters={
                    "school": "ISS",
                    "from_date": "2026-02-01",
                    "to_date": "2026-02-01",
                    "location": "SCI-LAB",
                }
            )

        self.assertEqual(payload["events"][0]["title"], "Teaching")
        self.assertEqual(payload["events"][0]["meta"]["teaching_context_label"], "Grade 8A · Biology")
        self.assertEqual(payload["events"][0]["meta"]["student_group_label"], "Grade 8A")
        self.assertEqual(payload["events"][0]["meta"]["course_name"], "Biology")

    def test_get_room_time_utilization_excludes_weekends_and_holidays_by_default(self):
        room_rows = [
            frappe._dict(
                {
                    "name": "ROOM-1",
                    "location_name": "Room 1",
                    "parent_location": "Main Building",
                    "location_type": "Classroom",
                    "location_type_name": "Classroom",
                }
            )
        ]
        calendar_rows = [
            frappe._dict(
                {
                    "name": "CAL-ISS-2026",
                    "school": "ISS",
                    "academic_year": "AY-2026",
                    "year_start_date": date(2025, 8, 1),
                    "year_end_date": date(2026, 6, 30),
                }
            )
        ]
        holiday_rows = [
            frappe._dict(
                {
                    "parent": "CAL-ISS-2026",
                    "holiday_date": date(2026, 2, 6),
                }
            )
        ]

        def mocked_get_all(doctype, *args, **kwargs):
            if doctype == "School Calendar Holidays":
                return holiday_rows
            return []

        with (
            patch("ifitwala_ed.api.room_utilization._require_room_utilization_analytics_access"),
            patch("ifitwala_ed.api.room_utilization._ensure_allowed_school", return_value="ISS"),
            patch(
                "ifitwala_ed.api.room_utilization._validate_date_range",
                return_value=(date(2026, 2, 6), date(2026, 2, 8), 3),
            ),
            patch(
                "ifitwala_ed.api.room_utilization._get_school_time_util_defaults",
                return_value={"day_start_time": "08:00:00", "day_end_time": "09:00:00"},
            ),
            patch("ifitwala_ed.api.room_utilization.resolve_school_calendars_for_window", return_value=calendar_rows),
            patch("ifitwala_ed.api.room_utilization.get_weekend_days_for_calendar", return_value=[6, 0]),
            patch("ifitwala_ed.api.room_utilization.frappe.get_all", side_effect=mocked_get_all),
            patch("ifitwala_ed.api.room_utilization.get_visible_location_rows_for_school", return_value=room_rows),
            patch("ifitwala_ed.api.room_utilization._require_location_booking_table"),
            patch("ifitwala_ed.api.room_utilization.frappe.db.has_column", return_value=True),
            patch("ifitwala_ed.api.room_utilization.frappe.db.get_all", return_value=[]),
        ):
            payload = room_utilization.get_room_time_utilization(
                filters={
                    "school": "ISS",
                    "from_date": "2026-02-06",
                    "to_date": "2026-02-08",
                }
            )

        self.assertFalse(payload["include_non_instructional_days"])
        self.assertEqual(payload["active_day_count"], 0)
        self.assertEqual(payload["rooms"][0]["available_minutes"], 0)

    def test_get_room_time_utilization_can_include_weekends_and_holidays(self):
        room_rows = [
            frappe._dict(
                {
                    "name": "ROOM-1",
                    "location_name": "Room 1",
                    "parent_location": "Main Building",
                    "location_type": "Classroom",
                    "location_type_name": "Classroom",
                }
            )
        ]

        with (
            patch("ifitwala_ed.api.room_utilization._require_room_utilization_analytics_access"),
            patch("ifitwala_ed.api.room_utilization._ensure_allowed_school", return_value="ISS"),
            patch(
                "ifitwala_ed.api.room_utilization._validate_date_range",
                return_value=(date(2026, 2, 6), date(2026, 2, 8), 3),
            ),
            patch(
                "ifitwala_ed.api.room_utilization._get_school_time_util_defaults",
                return_value={"day_start_time": "08:00:00", "day_end_time": "09:00:00"},
            ),
            patch("ifitwala_ed.api.room_utilization.get_visible_location_rows_for_school", return_value=room_rows),
            patch("ifitwala_ed.api.room_utilization._require_location_booking_table"),
            patch("ifitwala_ed.api.room_utilization.frappe.db.has_column", return_value=True),
            patch("ifitwala_ed.api.room_utilization.frappe.db.get_all", return_value=[]),
        ):
            payload = room_utilization.get_room_time_utilization(
                filters={
                    "school": "ISS",
                    "from_date": "2026-02-06",
                    "to_date": "2026-02-08",
                    "include_non_instructional_days": 1,
                }
            )

        self.assertTrue(payload["include_non_instructional_days"])
        self.assertEqual(payload["active_day_count"], 3)
        self.assertEqual(payload["rooms"][0]["available_minutes"], 180)
