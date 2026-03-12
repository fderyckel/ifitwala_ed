# ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py

from __future__ import annotations

import types
from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


class TestTaskDelivery(TestCase):
    def test_materialize_roster_generates_outcomes_for_eligible_students(self):
        task_delivery_service = types.ModuleType("ifitwala_ed.assessment.task_delivery_service")
        task_delivery_service.get_delivery_context = lambda student_group: {
            "course": "COURSE-1",
            "academic_year": "AY-2025-2026",
            "school": "SCHOOL-1",
        }
        task_delivery_service.get_eligible_students = Mock(return_value=["STU-1", "STU-2"])
        task_delivery_service.bulk_create_outcomes = Mock(return_value=2)
        task_delivery_service.resolve_or_create_lesson_instance = Mock(return_value=None)

        with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_delivery_service": task_delivery_service}):
            module = import_fresh("ifitwala_ed.assessment.doctype.task_delivery.task_delivery")

        delivery = module.TaskDelivery()
        delivery.delivery_mode = "Assess"
        delivery.grading_mode = "Criteria"
        delivery.student_group = "GRP-1"
        delivery._current_context = Mock(
            return_value={
                "course": "COURSE-1",
                "academic_year": "AY-2025-2026",
                "school": "SCHOOL-1",
            }
        )
        delivery._ensure_rubric_snapshot = Mock()

        result = delivery.materialize_roster()

        delivery._ensure_rubric_snapshot.assert_called_once_with()
        task_delivery_service.bulk_create_outcomes.assert_called_once_with(
            delivery,
            ["STU-1", "STU-2"],
            context={
                "course": "COURSE-1",
                "academic_year": "AY-2025-2026",
                "school": "SCHOOL-1",
            },
        )
        self.assertEqual(result, {"eligible_students": 2, "outcomes_created": 2})

    def test_validate_group_submission_accepts_zero_string(self):
        task_delivery_service = types.ModuleType("ifitwala_ed.assessment.task_delivery_service")
        task_delivery_service.get_delivery_context = lambda student_group: {}
        task_delivery_service.get_eligible_students = Mock(return_value=[])
        task_delivery_service.bulk_create_outcomes = Mock(return_value=0)
        task_delivery_service.resolve_or_create_lesson_instance = Mock(return_value=None)

        with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_delivery_service": task_delivery_service}):
            module = import_fresh("ifitwala_ed.assessment.doctype.task_delivery.task_delivery")

        delivery = module.TaskDelivery()
        delivery.group_submission = "0"

        delivery._validate_group_submission()

    def test_validate_group_submission_rejects_one_string(self):
        task_delivery_service = types.ModuleType("ifitwala_ed.assessment.task_delivery_service")
        task_delivery_service.get_delivery_context = lambda student_group: {}
        task_delivery_service.get_eligible_students = Mock(return_value=[])
        task_delivery_service.bulk_create_outcomes = Mock(return_value=0)
        task_delivery_service.resolve_or_create_lesson_instance = Mock(return_value=None)

        with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_delivery_service": task_delivery_service}):
            module = import_fresh("ifitwala_ed.assessment.doctype.task_delivery.task_delivery")

        delivery = module.TaskDelivery()
        delivery.group_submission = "1"

        with self.assertRaises(StubValidationError):
            delivery._validate_group_submission()
