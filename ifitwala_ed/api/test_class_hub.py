# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import json
from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from ifitwala_ed.api import class_hub


def _runtime_context(*, units=None, teaching_plan=True):
    return {
        "group": {
            "student_group_name": "Grade 7 A",
            "student_group_abbreviation": "G7-A",
            "course": "Science",
            "academic_year": "2025-2026",
        },
        "teaching_plan": {
            "class_teaching_plan": "CTP-001",
            "title": "Grade 7 A · Science",
            "course_plan": "CP-001",
            "planning_status": "Published",
        }
        if teaching_plan
        else None,
        "units": units or [],
        "resources": {
            "shared_resources": [],
            "class_resources": [],
            "general_assigned_work": [],
        },
    }


class _FakeClassSessionDoc:
    def __init__(self):
        self.name = "CLS-001"
        self.student_group = "SG-0001"
        self.class_teaching_plan = "CTP-001"
        self.unit_plan = "UP-001"
        self.title = "Evidence walk"
        self.session_date = "2026-04-02"
        self.sequence_index = 10
        self.learning_goal = "Explain change with evidence."
        self.teacher_note = "Watch the transition to guided practice."
        self.activities = [
            SimpleNamespace(
                title="Launch",
                activity_type="Discuss",
                estimated_minutes=10,
                sequence_index=10,
                student_direction="Share an initial claim.",
                teacher_prompt="What evidence supports that claim?",
                resource_note="Anchor chart",
            )
        ]

    def get(self, fieldname):
        return getattr(self, fieldname)


class TestClassHub(FrappeTestCase):
    def test_class_hub_group_names_includes_employee_booking_groups(self):
        def fake_get_all(doctype, filters=None, pluck=None, **kwargs):
            if doctype == "Employee Booking":
                self.assertEqual(filters.get("employee"), "EMP-001")
                self.assertEqual(filters.get("source_doctype"), "Student Group")
                return ["SG-BOOKED"]
            return []

        with (
            patch("ifitwala_ed.api.class_hub._instructor_group_names", return_value=set()),
            patch("ifitwala_ed.api.class_hub.frappe.db.table_exists", return_value=True),
            patch("ifitwala_ed.api.class_hub._resolve_employee_for_user", return_value={"name": "EMP-001"}),
            patch("ifitwala_ed.api.class_hub.frappe.get_all", side_effect=fake_get_all),
        ):
            group_names = class_hub._class_hub_group_names("teacher@example.com")

        self.assertEqual(group_names, {"SG-BOOKED"})

    def test_resolve_staff_home_entry_returns_single_group_when_only_one_is_taught(self):
        with (
            patch.object(class_hub.frappe, "session", SimpleNamespace(user="teacher@example.com")),
            patch("ifitwala_ed.api.class_hub._class_hub_group_names", return_value={"SG-0001"}),
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
            patch.object(class_hub.frappe, "session", SimpleNamespace(user="teacher@example.com")),
            patch("ifitwala_ed.api.class_hub._class_hub_group_names", return_value=set()),
        ):
            payload = class_hub.resolve_staff_home_entry()

        self.assertEqual(payload["status"], "empty")
        self.assertEqual(payload["groups"], [])
        self.assertIn("not assigned", payload["message"])

    def test_get_bundle_exposes_student_log_permission_from_doctype(self):
        with (
            patch("ifitwala_ed.api.class_hub._assert_instructor"),
            patch("ifitwala_ed.api.class_hub._resolve_runtime_context", return_value=_runtime_context()),
            patch(
                "ifitwala_ed.api.class_hub._get_active_roster",
                return_value=[{"student": "STU-001", "student_name": "Amina Dar"}],
            ),
            patch("ifitwala_ed.api.class_hub._can_create_student_log_for_session_user", return_value=True),
        ):
            payload = class_hub.get_bundle("SG-0001")

        self.assertTrue(payload["permissions"]["can_create_student_log"])

    def test_get_bundle_uses_real_class_session_payload(self):
        runtime = _runtime_context(
            units=[
                {
                    "unit_plan": "UP-001",
                    "title": "Matter and Change",
                    "teacher_focus": "Explain change using evidence.",
                    "essential_understanding": None,
                    "pacing_status": "In Progress",
                    "assigned_work": [],
                    "sessions": [
                        {
                            "class_session": "CLS-001",
                            "title": "Evidence walk",
                            "unit_plan": "UP-001",
                            "session_status": "Planned",
                            "session_date": "2026-04-02",
                            "sequence_index": 10,
                            "learning_goal": "Explain change using evidence.",
                            "teacher_note": "Keep the transition tight.",
                            "activities": [],
                            "resources": [{"title": "Observation sheet"}],
                            "assigned_work": [
                                {
                                    "task_delivery": "TD-001",
                                    "task": "TASK-001",
                                    "title": "Exit ticket",
                                    "due_date": "2026-04-03",
                                    "delivery_mode": "In class",
                                }
                            ],
                        }
                    ],
                }
            ]
        )

        with (
            patch("ifitwala_ed.api.class_hub._assert_instructor"),
            patch("ifitwala_ed.api.class_hub._resolve_runtime_context", return_value=runtime),
            patch(
                "ifitwala_ed.api.class_hub._get_active_roster",
                return_value=[{"student": "STU-001", "student_name": "Amina Dar"}],
            ),
            patch(
                "ifitwala_ed.api.class_hub._get_student_log_permissions", return_value={"can_create_student_log": True}
            ),
        ):
            payload = class_hub.get_bundle("SG-0001", date="2026-04-02", block_number=2)

        self.assertIsNone(payload["message"])
        self.assertEqual(payload["session"]["class_session"], "CLS-001")
        self.assertEqual(payload["session"]["status"], "planned")
        self.assertEqual(payload["task_items"][0]["id"], "TD-001")
        self.assertEqual(payload["today_items"][0]["overlay"], "QuickEvidence")
        self.assertEqual(payload["now"]["block_label"], "Block 2")

    def test_build_pulse_items_carry_unit_query_for_class_planning(self):
        payload = class_hub._build_pulse_items(
            student_group="SG-0001",
            current_session={
                "class_session": "CLS-001",
                "unit_plan": "UP-001",
                "resources": [{"title": "Observation sheet"}],
            },
            current_unit={"unit_plan": "UP-001"},
            task_items=[{"id": "TD-001", "title": "Exit ticket", "payload": {}}],
            date_iso="2026-04-02",
        )

        self.assertEqual(payload[0]["route"]["name"], "staff-class-planning")
        self.assertEqual(payload[0]["route"]["query"], {"unit_plan": "UP-001"})
        self.assertEqual(payload[1]["route"]["query"], {"unit_plan": "UP-001"})

    def test_assert_instructor_uses_canonical_group_membership_helper(self):
        with (
            patch("ifitwala_ed.api.class_hub.frappe.db.exists", return_value=True),
            patch("ifitwala_ed.api.class_hub._class_hub_group_names", return_value={"SG-0001"}),
            patch.object(class_hub.frappe, "session", SimpleNamespace(user="teacher@example.com")),
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
            patch.object(class_hub.frappe, "session", SimpleNamespace(user="teacher@example.com")),
            patch("ifitwala_ed.api.class_hub._resolve_employee_for_user", return_value={"name": "EMP-001"}),
            patch("ifitwala_ed.api.class_hub._class_hub_group_names", return_value={"SG-0001"}),
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
                side_effect=lambda value, _tz: get_datetime(value),
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
            patch.object(class_hub.frappe, "session", SimpleNamespace(user="teacher@example.com")),
            patch("ifitwala_ed.api.class_hub._resolve_employee_for_user", return_value={"name": "EMP-001"}),
            patch("ifitwala_ed.api.class_hub._class_hub_group_names", return_value={"SG-0001", "SG-0002"}),
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
                side_effect=lambda value, _tz: get_datetime(value),
            ),
        ):
            payload = class_hub.resolve_current_picker_context()

        self.assertEqual(payload["status"], "multiple_current")
        self.assertEqual(len(payload["contexts"]), 2)
        self.assertEqual(payload["contexts"][1]["student_group"], "SG-0002")

    def test_start_session_creates_minimal_session_from_current_unit(self):
        runtime = _runtime_context(
            units=[
                {
                    "unit_plan": "UP-001",
                    "title": "Matter and Change",
                    "teacher_focus": "Explain change using evidence.",
                    "essential_understanding": None,
                    "pacing_status": "In Progress",
                    "assigned_work": [],
                    "sessions": [],
                }
            ]
        )

        with (
            patch("ifitwala_ed.api.class_hub._assert_instructor"),
            patch("ifitwala_ed.api.class_hub._resolve_runtime_context", return_value=runtime),
            patch("ifitwala_ed.api.class_hub.planning.get_course_plan_row", return_value={"name": "CP-001"}),
            patch(
                "ifitwala_ed.api.class_hub.teaching_plans_api._resolve_current_curriculum_unit",
                return_value={
                    "unit_plan": "UP-001",
                    "unit": runtime["units"][0],
                    "source": "in_progress_unit",
                    "timeline": None,
                },
            ),
            patch(
                "ifitwala_ed.api.class_hub.teaching_plans_api.save_class_session",
                return_value={"class_session": "CLS-NEW", "session_status": "In Progress"},
            ) as save_session,
        ):
            payload = class_hub.start_session("SG-0001", date="2026-04-02")

        self.assertEqual(payload["class_session"], "CLS-NEW")
        self.assertEqual(payload["created"], 1)
        kwargs = save_session.call_args.kwargs
        self.assertEqual(kwargs["class_teaching_plan"], "CTP-001")
        self.assertEqual(kwargs["unit_plan"], "UP-001")
        self.assertEqual(kwargs["title"], "Matter and Change")
        self.assertEqual(kwargs["session_status"], "In Progress")
        self.assertEqual(kwargs["session_date"], "2026-04-02")

    def test_start_session_blocks_when_current_unit_cannot_be_resolved(self):
        runtime = _runtime_context(
            units=[
                {
                    "unit_plan": "UP-001",
                    "title": "Matter and Change",
                    "teacher_focus": "Explain change using evidence.",
                    "essential_understanding": None,
                    "pacing_status": "Not Started",
                    "assigned_work": [],
                    "sessions": [],
                }
            ]
        )

        with (
            patch("ifitwala_ed.api.class_hub._assert_instructor"),
            patch("ifitwala_ed.api.class_hub._resolve_runtime_context", return_value=runtime),
            patch("ifitwala_ed.api.class_hub.planning.get_course_plan_row", return_value={"name": "CP-001"}),
            patch(
                "ifitwala_ed.api.class_hub.teaching_plans_api._resolve_current_curriculum_unit",
                return_value={"unit_plan": None, "unit": None, "source": "none", "timeline": None},
            ),
        ):
            with self.assertRaises(class_hub.frappe.ValidationError):
                class_hub.start_session("SG-0001", date="2026-04-02")

    def test_start_session_reuses_existing_class_session_for_date(self):
        runtime = _runtime_context(
            units=[
                {
                    "unit_plan": "UP-001",
                    "title": "Matter and Change",
                    "teacher_focus": "Explain change using evidence.",
                    "essential_understanding": None,
                    "pacing_status": "In Progress",
                    "assigned_work": [],
                    "sessions": [
                        {
                            "class_session": "CLS-001",
                            "title": "Evidence walk",
                            "unit_plan": "UP-001",
                            "session_status": "Planned",
                            "session_date": "2026-04-02",
                            "sequence_index": 20,
                            "learning_goal": "Explain change using evidence.",
                            "teacher_note": "Keep the transition tight.",
                            "activities": [{"title": "Launch"}],
                            "resources": [],
                            "assigned_work": [],
                        }
                    ],
                }
            ]
        )

        with (
            patch("ifitwala_ed.api.class_hub._assert_instructor"),
            patch("ifitwala_ed.api.class_hub._resolve_runtime_context", return_value=runtime),
            patch(
                "ifitwala_ed.api.class_hub.teaching_plans_api.save_class_session",
                return_value={"class_session": "CLS-001", "session_status": "In Progress"},
            ) as save_session,
        ):
            payload = class_hub.start_session("SG-0001", date="2026-04-02")

        self.assertEqual(payload["class_session"], "CLS-001")
        self.assertEqual(payload["created"], 0)
        kwargs = save_session.call_args.kwargs
        self.assertEqual(kwargs["class_session"], "CLS-001")
        self.assertEqual(kwargs["title"], "Evidence walk")
        self.assertEqual(json.loads(kwargs["activities_json"])[0]["title"], "Launch")

    def test_end_session_marks_real_class_session_taught(self):
        with (
            patch.object(class_hub.frappe, "session", SimpleNamespace(user="teacher@example.com")),
            patch("ifitwala_ed.api.class_hub.frappe.get_doc", return_value=_FakeClassSessionDoc()),
            patch("ifitwala_ed.api.class_hub._assert_instructor"),
            patch(
                "ifitwala_ed.api.class_hub.teaching_plans_api.save_class_session",
                return_value={"class_session": "CLS-001", "session_status": "Taught"},
            ) as save_session,
        ):
            payload = class_hub.end_session("CLS-001")

        self.assertEqual(payload["status"], "ended")
        kwargs = save_session.call_args.kwargs
        self.assertEqual(kwargs["class_session"], "CLS-001")
        self.assertEqual(kwargs["session_status"], "Taught")
        self.assertEqual(json.loads(kwargs["activities_json"])[0]["title"], "Launch")
