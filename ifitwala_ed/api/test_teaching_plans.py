from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api import teaching_plans as teaching_plans_api


class TestTeachingPlansApi(TestCase):
    def test_build_staff_bundle_without_selected_plan_returns_empty_curriculum(self):
        with (
            patch(
                "ifitwala_ed.api.teaching_plans._resolve_staff_plan",
                return_value=(
                    {
                        "name": "GROUP-1",
                        "student_group_name": "Biology A",
                        "course": "COURSE-1",
                        "academic_year": "2025-2026",
                    },
                    [{"name": "COURSE-PLAN-1", "title": "Semester 1", "plan_status": "Active"}],
                    [],
                    None,
                ),
            ),
            patch("ifitwala_ed.api.teaching_plans.now_datetime") as now_datetime,
        ):
            now_datetime.return_value.isoformat.return_value = "2026-03-31 10:00:00"
            payload = teaching_plans_api._build_staff_bundle("GROUP-1")

        self.assertIsNone(payload["teaching_plan"])
        self.assertEqual(payload["curriculum"]["units"], [])
        self.assertEqual(payload["curriculum"]["session_count"], 0)

    def test_fetch_class_sessions_hides_teacher_fields_for_students(self):
        with (
            patch(
                "ifitwala_ed.api.teaching_plans.frappe.get_all",
                return_value=[
                    {
                        "name": "CLASS-SESSION-1",
                        "title": "Evidence walk",
                        "unit_plan": "UNIT-1",
                        "session_status": "Planned",
                        "session_date": None,
                        "sequence_index": 10,
                        "learning_goal": "Use evidence",
                        "teacher_note": "Teacher-only",
                    }
                ],
            ),
            patch(
                "ifitwala_ed.api.teaching_plans.frappe.db.sql",
                return_value=[
                    {
                        "parent": "CLASS-SESSION-1",
                        "title": "Observe",
                        "activity_type": "Discuss",
                        "estimated_minutes": 15,
                        "sequence_index": 10,
                        "student_direction": "Take notes.",
                        "teacher_prompt": "Push for precision.",
                        "resource_note": "Notebook needed.",
                        "idx": 1,
                    }
                ],
            ),
        ):
            payload = teaching_plans_api._fetch_class_sessions("CLASS-PLAN-1", audience="student")

        self.assertEqual(len(payload), 1)
        self.assertNotIn("teacher_note", payload[0])
        self.assertNotIn("teacher_prompt", payload[0]["activities"][0])
        self.assertEqual(payload[0]["activities"][0]["student_direction"], "Take notes.")

    def test_resolve_student_plan_reads_only_active_class_plans(self):
        with patch(
            "ifitwala_ed.api.teaching_plans.frappe.get_all",
            return_value=[
                {
                    "name": "CLASS-PLAN-1",
                    "title": "Biology A",
                    "course_plan": "COURSE-PLAN-1",
                    "planning_status": "Active",
                    "team_note": None,
                }
            ],
        ) as get_all:
            selected_group, class_plan_row = teaching_plans_api._resolve_student_plan(
                "COURSE-1",
                [{"student_group": "GROUP-1", "label": "Biology A"}],
                "GROUP-1",
            )

        self.assertEqual(selected_group, "GROUP-1")
        self.assertEqual(class_plan_row["name"], "CLASS-PLAN-1")
        self.assertEqual(get_all.call_args.kwargs["filters"]["planning_status"], "Active")
