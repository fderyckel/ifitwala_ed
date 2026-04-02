# ifitwala_ed/api/test_courses.py

from datetime import datetime
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api import courses as courses_api


class TestCoursesApi(TestCase):
    def test_get_courses_data_includes_learning_space_readiness(self):
        with (
            patch.object(courses_api.frappe, "session", SimpleNamespace(user="student@example.com")),
            patch.object(courses_api.frappe, "get_roles", return_value=["Student"]),
            patch.object(courses_api, "_get_student_name_for_user", return_value="STU-001"),
            patch.object(courses_api, "_get_academic_years", return_value=["2025-2026"]),
            patch.object(
                courses_api,
                "_build_student_course_scope",
                return_value={
                    "COURSE-1": {
                        "student_groups": [
                            {
                                "student_group": "GROUP-1",
                                "student_group_name": "Biology A",
                                "academic_year": "2025-2026",
                            }
                        ]
                    },
                    "COURSE-2": {"student_groups": []},
                    "COURSE-3": {
                        "student_groups": [
                            {
                                "student_group": "GROUP-3",
                                "student_group_name": "History A",
                                "academic_year": "2025-2026",
                            }
                        ]
                    },
                },
            ),
            patch.object(
                courses_api,
                "_get_courses_for_year",
                return_value=[
                    {
                        "course": "COURSE-1",
                        "course_name": "Biology",
                        "course_group": "Science",
                        "course_image": "/files/biology.jpg",
                        "href": {"name": "student-course-detail", "params": {"course_id": "COURSE-1"}},
                    },
                    {
                        "course": "COURSE-2",
                        "course_name": "Design",
                        "course_group": "Arts",
                        "course_image": "/files/design.jpg",
                        "href": {"name": "student-course-detail", "params": {"course_id": "COURSE-2"}},
                    },
                    {
                        "course": "COURSE-3",
                        "course_name": "History",
                        "course_group": "Humanities",
                        "course_image": "/files/history.jpg",
                        "href": {"name": "student-course-detail", "params": {"course_id": "COURSE-3"}},
                    },
                ],
            ),
            patch.object(courses_api, "_fetch_active_class_plan_groups", return_value={"GROUP-1"}),
            patch.object(
                courses_api,
                "_fetch_active_course_plan_counts",
                return_value={"COURSE-1": 0, "COURSE-2": 1, "COURSE-3": 0},
            ),
        ):
            payload = courses_api.get_courses_data("2025-2026")

        self.assertEqual(payload["courses"][0]["learning_space"]["status"], "ready")
        self.assertEqual(payload["courses"][0]["learning_space"]["cta_label"], "Open class")
        self.assertEqual(payload["courses"][1]["learning_space"]["status"], "shared_plan_only")
        self.assertEqual(payload["courses"][1]["learning_space"]["cta_label"], "Open shared plan")
        self.assertEqual(payload["courses"][2]["learning_space"]["status"], "awaiting_class_plan")
        self.assertEqual(payload["courses"][2]["learning_space"]["can_open"], 0)
        self.assertIsNone(payload["courses"][2]["href"])

    def test_get_student_hub_home_prefers_today_class_for_next_step(self):
        anchor = datetime(2026, 3, 12, 8, 45, 0)
        with (
            patch("ifitwala_ed.api.courses._require_student_name_for_session_user", return_value="STU-001"),
            patch("ifitwala_ed.api.courses._build_student_course_scope", return_value={"COURSE-1": {}}),
            patch("ifitwala_ed.api.courses.now_datetime", return_value=anchor),
            patch(
                "ifitwala_ed.api.courses.portal_api.get_student_portal_identity",
                return_value={"display_name": "Amina", "student": "STU-001", "user": "student@example.com"},
            ),
            patch(
                "ifitwala_ed.api.courses.course_schedule_api.get_today_courses",
                return_value={
                    "date": "2026-03-12",
                    "weekday": "Thursday",
                    "courses": [
                        {
                            "course": "COURSE-1",
                            "course_name": "Biology",
                            "time_slots": [
                                {
                                    "from_time": "10:00",
                                    "to_time": "11:00",
                                    "time_range": "10:00 - 11:00",
                                }
                            ],
                            "href": {"name": "student-course-detail", "params": {"course_id": "COURSE-1"}},
                        }
                    ],
                },
            ),
            patch(
                "ifitwala_ed.api.courses.get_courses_data",
                return_value={"selected_year": "2025-2026", "courses": []},
            ),
        ):
            payload = courses_api.get_student_hub_home()

        self.assertEqual(payload["identity"]["display_name"], "Amina")
        self.assertEqual(payload["learning"]["today_classes"][0]["course"], "COURSE-1")
        self.assertEqual(payload["learning"]["next_learning_step"]["kind"], "scheduled_class")
        self.assertEqual(payload["learning"]["next_learning_step"]["title"], "Biology")

    def test_get_student_hub_home_falls_back_to_first_accessible_course(self):
        with (
            patch("ifitwala_ed.api.courses._require_student_name_for_session_user", return_value="STU-001"),
            patch(
                "ifitwala_ed.api.courses._build_student_course_scope",
                return_value={"COURSE-1": {}, "COURSE-2": {}},
            ),
            patch(
                "ifitwala_ed.api.courses.portal_api.get_student_portal_identity",
                return_value={"display_name": "Amina", "student": "STU-001", "user": "student@example.com"},
            ),
            patch(
                "ifitwala_ed.api.courses.course_schedule_api.get_today_courses",
                return_value={"date": "2026-03-12", "weekday": "Thursday", "courses": []},
            ),
            patch(
                "ifitwala_ed.api.courses.get_courses_data",
                return_value={
                    "selected_year": "2025-2026",
                    "courses": [
                        {
                            "course": "COURSE-2",
                            "course_name": "History",
                            "href": {"name": "student-course-detail", "params": {"course_id": "COURSE-2"}},
                        }
                    ],
                },
            ),
        ):
            payload = courses_api.get_student_hub_home()

        self.assertEqual(payload["learning"]["next_learning_step"]["kind"], "course")
        self.assertEqual(payload["learning"]["next_learning_step"]["title"], "History")
        self.assertEqual(payload["learning"]["accessible_courses_count"], 2)

    def test_get_student_hub_home_prefers_first_openable_course_when_first_course_is_blocked(self):
        with (
            patch("ifitwala_ed.api.courses._require_student_name_for_session_user", return_value="STU-001"),
            patch(
                "ifitwala_ed.api.courses._build_student_courses_payload",
                return_value=(
                    {
                        "selected_year": "2025-2026",
                        "courses": [
                            {
                                "course": "COURSE-1",
                                "course_name": "Biology",
                                "href": None,
                                "learning_space": {
                                    "status": "awaiting_class_assignment",
                                    "status_label": "Class Assignment Pending",
                                    "summary": "Your class is still being assigned.",
                                    "cta_label": "Not ready yet",
                                    "can_open": 0,
                                    "href": None,
                                },
                            },
                            {
                                "course": "COURSE-2",
                                "course_name": "History",
                                "href": {"name": "student-course-detail", "params": {"course_id": "COURSE-2"}},
                                "learning_space": {
                                    "status": "shared_plan_only",
                                    "status_label": "Shared Plan",
                                    "summary": "Open the shared course plan for now.",
                                    "cta_label": "Open shared plan",
                                    "can_open": 1,
                                    "href": {
                                        "name": "student-course-detail",
                                        "params": {"course_id": "COURSE-2"},
                                    },
                                },
                            },
                        ],
                    },
                    {"COURSE-1": {}, "COURSE-2": {}},
                ),
            ),
            patch(
                "ifitwala_ed.api.courses.portal_api.get_student_portal_identity",
                return_value={"display_name": "Amina", "student": "STU-001", "user": "student@example.com"},
            ),
            patch(
                "ifitwala_ed.api.courses.course_schedule_api.get_today_courses",
                return_value={"date": "2026-03-12", "weekday": "Thursday", "courses": []},
            ),
            patch(
                "ifitwala_ed.api.courses._fetch_student_hub_task_rows",
                return_value=[],
            ),
        ):
            payload = courses_api.get_student_hub_home()

        self.assertEqual(payload["learning"]["next_learning_step"]["title"], "History")
        self.assertEqual(payload["learning"]["next_learning_step"]["cta_label"], "Open shared plan")
        self.assertEqual(payload["learning"]["next_learning_step"]["status_label"], "Shared Plan")
        self.assertEqual(payload["learning"]["next_learning_step"]["can_open"], 1)

    def test_build_home_orientation_finds_current_and_next_class(self):
        anchor = datetime(2026, 3, 13, 9, 15, 0)
        orientation = courses_api._build_home_orientation(
            [
                {
                    "course": "COURSE-1",
                    "course_name": "Biology",
                    "time_slots": [{"from_time": "08:30", "to_time": "09:30"}],
                },
                {
                    "course": "COURSE-2",
                    "course_name": "History",
                    "time_slots": [{"from_time": "10:00", "to_time": "11:00"}],
                },
            ],
            anchor,
        )

        self.assertEqual(orientation["current_class"]["course"], "COURSE-1")
        self.assertEqual(orientation["next_class"]["course"], "COURSE-2")

    def test_build_work_board_payload_sorts_open_and_done_lanes(self):
        anchor = datetime(2026, 3, 13, 9, 0, 0)
        board = courses_api._build_work_board_payload(
            [
                {
                    "task_delivery": "TD-OVERDUE",
                    "task": "TASK-1",
                    "title": "Overdue essay",
                    "course": "COURSE-1",
                    "course_name": "Biology",
                    "due_date": "2026-03-12 09:00:00",
                    "submission_status": "Not Submitted",
                    "grading_status": "Not Started",
                    "has_submission": 0,
                    "is_complete": 0,
                },
                {
                    "task_delivery": "TD-SOON",
                    "task": "TASK-2",
                    "title": "Quiz review",
                    "course": "COURSE-1",
                    "course_name": "Biology",
                    "due_date": "2026-03-18 09:00:00",
                    "submission_status": "Not Submitted",
                    "grading_status": "Not Started",
                    "has_submission": 0,
                    "is_complete": 0,
                },
                {
                    "task_delivery": "TD-LATER",
                    "task": "TASK-3",
                    "title": "Long-term project",
                    "course": "COURSE-2",
                    "course_name": "History",
                    "due_date": "2026-03-28 09:00:00",
                    "submission_status": "Not Submitted",
                    "grading_status": "Not Started",
                    "has_submission": 0,
                    "is_complete": 0,
                },
                {
                    "task_delivery": "TD-DONE",
                    "task": "TASK-4",
                    "title": "Submitted report",
                    "course": "COURSE-2",
                    "course_name": "History",
                    "submission_status": "Submitted",
                    "grading_status": "Not Started",
                    "has_submission": 1,
                    "is_complete": 0,
                    "completed_on": "2026-03-13 08:00:00",
                },
            ],
            anchor,
        )

        self.assertEqual([item["task_delivery"] for item in board["now"]], ["TD-OVERDUE"])
        self.assertEqual([item["task_delivery"] for item in board["soon"]], ["TD-SOON"])
        self.assertEqual([item["task_delivery"] for item in board["later"]], ["TD-LATER"])
        self.assertEqual([item["task_delivery"] for item in board["done"]], ["TD-DONE"])

    def test_get_student_hub_home_includes_board_and_timeline(self):
        anchor = datetime(2026, 3, 13, 8, 45, 0)
        with (
            patch("ifitwala_ed.api.courses._require_student_name_for_session_user", return_value="STU-001"),
            patch(
                "ifitwala_ed.api.courses._build_student_course_scope",
                return_value={
                    "COURSE-1": {
                        "student_groups": [{"student_group": "GROUP-1"}],
                    }
                },
            ),
            patch("ifitwala_ed.api.courses.now_datetime", return_value=anchor),
            patch(
                "ifitwala_ed.api.courses.portal_api.get_student_portal_identity",
                return_value={"display_name": "Amina", "student": "STU-001", "user": "student@example.com"},
            ),
            patch(
                "ifitwala_ed.api.courses.course_schedule_api.get_today_courses",
                return_value={
                    "date": "2026-03-13",
                    "weekday": "Friday",
                    "courses": [
                        {
                            "course": "COURSE-1",
                            "course_name": "Biology",
                            "student_group": "GROUP-1",
                            "student_group_name": "Biology 8A",
                            "time_slots": [{"from_time": "10:00", "to_time": "11:00", "time_range": "10:00 - 11:00"}],
                            "href": {"name": "student-course-detail", "params": {"course_id": "COURSE-1"}},
                        }
                    ],
                },
            ),
            patch(
                "ifitwala_ed.api.courses.get_courses_data",
                return_value={"selected_year": "2025-2026", "courses": []},
            ),
            patch(
                "ifitwala_ed.api.courses._fetch_student_hub_task_rows",
                return_value=[
                    {
                        "task_delivery": "TD-1",
                        "task": "TASK-1",
                        "title": "Lab notes",
                        "course": "COURSE-1",
                        "course_name": "Biology",
                        "student_group": "GROUP-1",
                        "delivery_mode": "Collect Work",
                        "requires_submission": 1,
                        "require_grading": 1,
                        "due_date": "2026-03-14 09:00:00",
                        "unit_plan": "LU-1",
                        "lesson": "LESSON-1",
                        "class_session": "CLASS-SESSION-1",
                        "submission_status": "Not Submitted",
                        "grading_status": "Not Started",
                        "has_submission": 0,
                        "has_new_submission": 0,
                        "is_complete": 0,
                    }
                ],
            ),
        ):
            payload = courses_api.get_student_hub_home()

        self.assertIn("orientation", payload["learning"])
        self.assertIn("work_board", payload["learning"])
        self.assertIn("timeline", payload["learning"])
        self.assertEqual(payload["learning"]["work_board"]["now"][0]["task_delivery"], "TD-1")
        self.assertEqual(
            payload["learning"]["work_board"]["now"][0]["href"]["query"]["student_group"],
            "GROUP-1",
        )
        self.assertEqual(payload["learning"]["timeline"][0]["items"][0]["kind"], "scheduled_class")
