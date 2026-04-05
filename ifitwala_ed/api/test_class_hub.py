# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import class_hub


class TestClassHub(FrappeTestCase):
    def test_resolve_staff_home_entry_returns_single_group_when_only_one_is_taught(self):
        with (
            patch("ifitwala_ed.api.class_hub.frappe.session.user", "teacher@example.com"),
            patch("ifitwala_ed.api.class_hub._instructor_group_names", return_value={"SG-0001"}),
            patch(
                "ifitwala_ed.api.class_hub.frappe.get_all",
                return_value=[
                    {
                        "name": "SG-0001",
                        "student_group_name": "Grade 7 A",
                        "student_group_abbreviation": "G7-A",
                        "course": "Science",
                        "academic_year": "2025-2026",
                    }
                ],
            ),
        ):
            payload = class_hub.resolve_staff_home_entry()

        self.assertEqual(payload["status"], "single")
        self.assertEqual(payload["groups"][0]["student_group"], "SG-0001")
        self.assertEqual(payload["groups"][0]["title"], "G7-A - Science")

    def test_resolve_staff_home_entry_returns_empty_state_without_groups(self):
        with (
            patch("ifitwala_ed.api.class_hub.frappe.session.user", "teacher@example.com"),
            patch("ifitwala_ed.api.class_hub._instructor_group_names", return_value=set()),
        ):
            payload = class_hub.resolve_staff_home_entry()

        self.assertEqual(payload["status"], "empty")
        self.assertEqual(payload["groups"], [])
        self.assertIn("not assigned", payload["message"])

    def test_get_bundle_exposes_student_log_permission_from_doctype(self):
        with (
            patch("ifitwala_ed.api.class_hub._assert_instructor"),
            patch(
                "ifitwala_ed.api.class_hub.frappe.db.get_value",
                return_value={
                    "student_group_abbreviation": "G7-A",
                    "student_group_name": "Grade 7 A",
                    "course": "Science",
                    "academic_year": "2025-2026",
                },
            ),
            patch(
                "ifitwala_ed.api.class_hub.frappe.get_all",
                return_value=[{"student": "STU-001", "student_name": "Amina Dar"}],
            ),
            patch(
                "ifitwala_ed.api.class_hub._can_create_student_log_for_session_user",
                return_value=True,
            ),
        ):
            payload = class_hub.get_bundle("SG-0001")

        self.assertTrue(payload["permissions"]["can_create_student_log"])

    def test_assert_instructor_uses_canonical_group_membership_helper(self):
        with (
            patch("ifitwala_ed.api.class_hub.frappe.db.exists", return_value=True),
            patch("ifitwala_ed.api.class_hub._instructor_group_names", return_value={"SG-0001"}),
            patch("ifitwala_ed.api.class_hub.frappe.session.user", "teacher@example.com"),
        ):
            class_hub._assert_instructor("SG-0001")

    def test_resolve_current_picker_context_returns_ready_context(self):
        current_row = {
            "booking_name": "BOOK-001",
            "student_group": "SG-0001",
            "from_datetime": "2026-04-02 08:45:00",
            "to_datetime": "2026-04-02 09:30:00",
            "location": "Room 204",
        }

        with (
            patch("ifitwala_ed.api.class_hub.frappe.session.user", "teacher@example.com"),
            patch("ifitwala_ed.api.class_hub._resolve_employee_for_user", return_value={"name": "EMP-001"}),
            patch("ifitwala_ed.api.class_hub._instructor_group_names", return_value={"SG-0001"}),
            patch("ifitwala_ed.api.class_hub._resolve_live_class_rows", return_value=([current_row], None)),
            patch(
                "ifitwala_ed.api.class_hub.frappe.db.get_value",
                return_value={
                    "student_group_abbreviation": "G7-A",
                    "student_group_name": "Grade 7 A",
                    "course": "Science",
                    "academic_year": "2025-2026",
                },
            ),
            patch(
                "ifitwala_ed.api.class_hub.frappe.get_all",
                return_value=[{"student": "STU-001", "student_name": "Amina Dar"}],
            ),
            patch(
                "ifitwala_ed.api.class_hub._can_create_student_log_for_session_user",
                return_value=True,
            ),
            patch("ifitwala_ed.api.class_hub._system_tzinfo"),
            patch(
                "ifitwala_ed.api.class_hub._to_system_datetime",
                side_effect=lambda value, _tz: value,
            ),
        ):
            payload = class_hub.resolve_current_picker_context()

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(len(payload["contexts"]), 1)
        self.assertEqual(payload["contexts"][0]["student_group"], "SG-0001")
        self.assertTrue(payload["contexts"][0]["permissions"]["can_create_student_log"])

    def test_resolve_current_picker_context_returns_multiple_current_options(self):
        current_rows = [
            {
                "booking_name": "BOOK-001",
                "student_group": "SG-0001",
                "from_datetime": "2026-04-02 08:45:00",
                "to_datetime": "2026-04-02 09:30:00",
                "location": "Room 204",
            },
            {
                "booking_name": "BOOK-002",
                "student_group": "SG-0002",
                "from_datetime": "2026-04-02 08:50:00",
                "to_datetime": "2026-04-02 09:35:00",
                "location": "Lab 1",
            },
        ]

        def fake_group_row(doctype, name, fields, as_dict=False):
            if doctype != "Student Group":
                return None
            if name == "SG-0001":
                return {
                    "student_group_abbreviation": "G7-A",
                    "student_group_name": "Grade 7 A",
                    "course": "Science",
                    "academic_year": "2025-2026",
                }
            return {
                "student_group_abbreviation": "G7-B",
                "student_group_name": "Grade 7 B",
                "course": "Math",
                "academic_year": "2025-2026",
            }

        def fake_roster(doctype, filters=None, fields=None, order_by=None):
            return [
                {
                    "student": f"{filters['parent']}-STU-001",
                    "student_name": f"{filters['parent']} Student",
                }
            ]

        with (
            patch("ifitwala_ed.api.class_hub.frappe.session.user", "teacher@example.com"),
            patch("ifitwala_ed.api.class_hub._resolve_employee_for_user", return_value={"name": "EMP-001"}),
            patch("ifitwala_ed.api.class_hub._instructor_group_names", return_value={"SG-0001", "SG-0002"}),
            patch("ifitwala_ed.api.class_hub._resolve_live_class_rows", return_value=(current_rows, None)),
            patch("ifitwala_ed.api.class_hub.frappe.db.get_value", side_effect=fake_group_row),
            patch("ifitwala_ed.api.class_hub.frappe.get_all", side_effect=fake_roster),
            patch(
                "ifitwala_ed.api.class_hub._can_create_student_log_for_session_user",
                return_value=False,
            ),
            patch("ifitwala_ed.api.class_hub._system_tzinfo"),
            patch(
                "ifitwala_ed.api.class_hub._to_system_datetime",
                side_effect=lambda value, _tz: value,
            ),
        ):
            payload = class_hub.resolve_current_picker_context()

        self.assertEqual(payload["status"], "multiple_current")
        self.assertEqual(len(payload["contexts"]), 2)
        self.assertEqual(payload["contexts"][1]["student_group"], "SG-0002")
