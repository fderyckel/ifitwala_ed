# ifitwala_ed/api/test_room_utilization.py

from datetime import date
from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import room_utilization


class TestRoomUtilizationApi(TestCase):
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
