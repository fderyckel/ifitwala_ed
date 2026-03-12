# ifitwala_ed/api/test_courses.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import courses as courses_api


class TestCoursesApi(TestCase):
    def test_get_student_hub_home_prefers_today_class_for_next_step(self):
        with (
            patch("ifitwala_ed.api.courses._require_student_name_for_session_user", return_value="STU-001"),
            patch("ifitwala_ed.api.courses._build_student_course_scope", return_value={"COURSE-1": {}}),
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

    def test_resolve_deep_link_context_uses_lesson_instance_activity_parent(self):
        result = courses_api._resolve_deep_link_context(
            requested_learning_unit=None,
            requested_lesson=None,
            requested_lesson_instance="LI-1",
            units_by_name={"LU-1": {"name": "LU-1", "unit_order": 1, "lessons": [{"name": "LESSON-1"}]}},
            lessons_by_name={"LESSON-1": {"name": "LESSON-1", "learning_unit": "LU-1"}},
            activities_by_name={"ACT-1": {"name": "ACT-1", "lesson": "LESSON-1"}},
            lesson_instances_by_name={
                "LI-1": {
                    "name": "LI-1",
                    "lesson": None,
                    "lesson_activity": "ACT-1",
                    "student_group": "GROUP-1",
                }
            },
        )

        self.assertEqual(result["resolved"]["source"], "lesson_instance")
        self.assertEqual(result["resolved"]["lesson_instance"], "LI-1")
        self.assertEqual(result["resolved"]["lesson"], "LESSON-1")
        self.assertEqual(result["resolved"]["learning_unit"], "LU-1")

    def test_build_curriculum_payload_buckets_tasks_by_anchor(self):
        curriculum, _maps = courses_api._build_curriculum_payload(
            units=[{"name": "LU-1", "unit_name": "Unit 1", "unit_order": 1}],
            lessons=[
                {
                    "name": "LESSON-1",
                    "learning_unit": "LU-1",
                    "title": "Lesson 1",
                    "lesson_order": 1,
                }
            ],
            activities=[
                {
                    "name": "ACT-1",
                    "lesson": "LESSON-1",
                    "title": "Read",
                    "activity_type": "Reading",
                    "lesson_activity_order": 1,
                }
            ],
            tasks=[
                {"name": "TASK-COURSE", "title": "Course task", "task_type": "Assignment"},
                {
                    "name": "TASK-UNIT",
                    "title": "Unit task",
                    "task_type": "Assignment",
                    "learning_unit": "LU-1",
                },
                {
                    "name": "TASK-LESSON",
                    "title": "Lesson task",
                    "task_type": "Quiz",
                    "lesson": "LESSON-1",
                },
            ],
            deliveries=[
                {"name": "TD-1", "task": "TASK-UNIT", "student_group": "GROUP-1"},
                {"name": "TD-2", "task": "TASK-LESSON", "student_group": "GROUP-1"},
            ],
        )

        self.assertEqual(curriculum["counts"]["units"], 1)
        self.assertEqual(curriculum["counts"]["lessons"], 1)
        self.assertEqual(curriculum["counts"]["activities"], 1)
        self.assertEqual(curriculum["counts"]["course_tasks"], 1)
        self.assertEqual(curriculum["counts"]["unit_tasks"], 1)
        self.assertEqual(curriculum["counts"]["lesson_tasks"], 1)
        self.assertEqual(curriculum["counts"]["deliveries"], 2)
        self.assertEqual(len(curriculum["course_tasks"]), 1)
        self.assertEqual(len(curriculum["units"][0]["linked_tasks"]), 1)
        self.assertEqual(len(curriculum["units"][0]["lessons"][0]["linked_tasks"]), 1)

    def test_get_student_course_detail_rejects_out_of_scope_course(self):
        with (
            patch("ifitwala_ed.api.courses._require_student_name_for_session_user", return_value="STU-001"),
            patch("ifitwala_ed.api.courses._build_student_course_scope", return_value={}),
        ):
            with self.assertRaises(frappe.PermissionError):
                courses_api.get_student_course_detail(course_id="COURSE-404")
