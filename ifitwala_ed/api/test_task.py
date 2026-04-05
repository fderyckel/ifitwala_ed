# ifitwala_ed/api/test_task.py

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubPermissionError, import_fresh, stubbed_frappe


def _task_service_stub():
    module = types.ModuleType("ifitwala_ed.assessment.task_delivery_service")
    module.resolve_planning_context = lambda student_group, class_teaching_plan=None, class_session=None: {
        "class_teaching_plan": class_teaching_plan or "CLASS-PLAN-1",
        "class_session": class_session,
        "course": "COURSE-1",
        "academic_year": "AY-2025-2026",
        "unit_plan": None,
    }
    module.create_delivery = lambda payload: {"task_delivery": "TDL-0001", "outcomes_created": 24}
    return module


class TestTaskApi(TestCase):
    def test_search_reusable_tasks_returns_own_and_course_shared_tasks_only(self):
        permission_calls: list[tuple[str, str, tuple[str, ...] | None, str | None]] = []
        sql_calls: list[tuple[str, dict, bool]] = []

        planning_module = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning_module.assert_can_manage_course_curriculum = lambda user, course, roles=None, action_label=None: (
            permission_calls.append((user, course, tuple(roles or []), action_label))
        )
        planning_module.assert_can_read_course_curriculum = planning_module.assert_can_manage_course_curriculum

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning_module,
                "ifitwala_ed.assessment.task_delivery_service": _task_service_stub(),
            }
        ) as frappe:
            frappe.get_roles = lambda user: ["Instructor"]

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Student Group":
                    return "COURSE-1"
                return None

            def fake_sql(query, params=None, as_dict=False):
                sql_calls.append((query, params or {}, as_dict))
                return [
                    {
                        "name": "TASK-OWN-1",
                        "title": "Personal draft",
                        "task_type": "Assignment",
                        "default_course": "COURSE-1",
                        "unit_plan": "UNIT-1",
                        "owner": "unit.test@example.com",
                        "is_template": 0,
                        "modified": "2026-04-05 10:00:00",
                    },
                    {
                        "name": "TASK-SHARED-1",
                        "title": "Shared reading response",
                        "task_type": "Homework",
                        "default_course": "COURSE-1",
                        "unit_plan": "",
                        "owner": "colleague@example.com",
                        "is_template": 1,
                        "modified": "2026-04-04 09:00:00",
                    },
                    {
                        "name": "TASK-PRIVATE-OTHER",
                        "title": "Hidden draft",
                        "task_type": "Homework",
                        "default_course": "COURSE-1",
                        "unit_plan": "",
                        "owner": "colleague@example.com",
                        "is_template": 0,
                        "modified": "2026-04-03 08:00:00",
                    },
                ]

            frappe.db.get_value = fake_get_value
            frappe.db.sql = fake_sql

            module = import_fresh("ifitwala_ed.api.task")
            payload = module.search_reusable_tasks(
                student_group="GRP-1",
                unit_plan="UNIT-1",
                query="reading",
                scope="all",
            )

        self.assertEqual(
            permission_calls,
            [
                (
                    "unit.test@example.com",
                    "COURSE-1",
                    ("Instructor",),
                    "reuse tasks for this course",
                )
            ],
        )
        self.assertEqual(sql_calls[0][2], True)
        self.assertEqual(sql_calls[0][1]["course"], "COURSE-1")
        self.assertEqual(sql_calls[0][1]["query"], "%reading%")
        self.assertEqual(sql_calls[0][1]["unit_plan"], "UNIT-1")
        self.assertEqual(
            payload,
            [
                {
                    "name": "TASK-OWN-1",
                    "title": "Personal draft",
                    "task_type": "Assignment",
                    "default_course": "COURSE-1",
                    "unit_plan": "UNIT-1",
                    "owner": "unit.test@example.com",
                    "is_template": 0,
                    "modified": "2026-04-05 10:00:00",
                    "visibility_scope": "mine",
                    "visibility_label": "Your task",
                },
                {
                    "name": "TASK-SHARED-1",
                    "title": "Shared reading response",
                    "task_type": "Homework",
                    "default_course": "COURSE-1",
                    "unit_plan": "",
                    "owner": "colleague@example.com",
                    "is_template": 1,
                    "modified": "2026-04-04 09:00:00",
                    "visibility_scope": "shared",
                    "visibility_label": "Shared with course team",
                },
            ],
        )

    def test_create_task_delivery_rejects_unshared_task_owned_by_another_teacher(self):
        planning_module = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning_module.assert_can_manage_course_curriculum = lambda *args, **kwargs: None
        planning_module.assert_can_read_course_curriculum = lambda *args, **kwargs: None

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning_module,
                "ifitwala_ed.assessment.task_delivery_service": _task_service_stub(),
            }
        ) as frappe:
            frappe.get_roles = lambda user: ["Instructor"]

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task":
                    return {
                        "name": "TASK-PRIVATE-OTHER",
                        "title": "Private task",
                        "instructions": None,
                        "task_type": "Assignment",
                        "default_course": "COURSE-1",
                        "unit_plan": None,
                        "is_template": 0,
                        "is_archived": 0,
                        "owner": "colleague@example.com",
                        "default_delivery_mode": "Assign Only",
                        "default_allow_feedback": 0,
                        "default_grading_mode": "None",
                        "default_max_points": None,
                        "default_grade_scale": None,
                        "quiz_question_bank": None,
                        "quiz_question_count": None,
                        "quiz_time_limit_minutes": None,
                        "quiz_max_attempts": None,
                        "quiz_pass_percentage": None,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.api.task")
            with self.assertRaises(StubPermissionError):
                module.create_task_delivery({"task": "TASK-PRIVATE-OTHER", "student_group": "GRP-1"})

    def test_get_task_for_delivery_returns_shared_task_details(self):
        permission_calls: list[tuple[str, str, tuple[str, ...] | None, str | None]] = []
        planning_module = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning_module.assert_can_manage_course_curriculum = lambda user, course, roles=None, action_label=None: (
            permission_calls.append((user, course, tuple(roles or []), action_label))
        )
        planning_module.assert_can_read_course_curriculum = lambda *args, **kwargs: None

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": planning_module,
                "ifitwala_ed.assessment.task_delivery_service": _task_service_stub(),
            }
        ) as frappe:
            frappe.get_roles = lambda user: ["Instructor"]

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Student Group":
                    return "COURSE-1"
                if doctype == "Task":
                    return {
                        "name": "TASK-SHARED-1",
                        "title": "Shared reading response",
                        "instructions": "<p>Annotate the article and answer the prompts.</p>",
                        "task_type": "Homework",
                        "default_course": "COURSE-1",
                        "unit_plan": "UNIT-1",
                        "is_template": 1,
                        "is_archived": 0,
                        "owner": "colleague@example.com",
                        "default_delivery_mode": "Collect Work",
                        "default_allow_feedback": 1,
                        "default_grading_mode": "Completion",
                        "default_max_points": None,
                        "default_grade_scale": None,
                        "quiz_question_bank": None,
                        "quiz_question_count": None,
                        "quiz_time_limit_minutes": None,
                        "quiz_max_attempts": None,
                        "quiz_pass_percentage": None,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.api.task")
            payload = module.get_task_for_delivery("TASK-SHARED-1", student_group="GRP-1")

        self.assertEqual(
            permission_calls,
            [
                (
                    "unit.test@example.com",
                    "COURSE-1",
                    ("Instructor",),
                    "reuse tasks for this course",
                )
            ],
        )
        self.assertEqual(payload["visibility_scope"], "shared")
        self.assertEqual(payload["default_delivery_mode"], "Collect Work")
        self.assertEqual(payload["grading_defaults"]["default_grading_mode"], "Completion")
        self.assertEqual(payload["title"], "Shared reading response")
