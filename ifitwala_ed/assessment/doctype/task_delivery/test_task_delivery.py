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

        with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_delivery_service": task_delivery_service}):
            module = import_fresh("ifitwala_ed.assessment.doctype.task_delivery.task_delivery")

        delivery = module.TaskDelivery()
        delivery.group_submission = "1"

        with self.assertRaises(StubValidationError):
            delivery._validate_group_submission()

    def test_apply_delivery_mode_defaults_for_assessed_quiz_forces_points_without_submission(self):
        task_delivery_service = types.ModuleType("ifitwala_ed.assessment.task_delivery_service")
        task_delivery_service.get_delivery_context = lambda student_group: {}
        task_delivery_service.get_eligible_students = Mock(return_value=[])
        task_delivery_service.bulk_create_outcomes = Mock(return_value=0)

        with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_delivery_service": task_delivery_service}):
            module = import_fresh("ifitwala_ed.assessment.doctype.task_delivery.task_delivery")

        delivery = module.TaskDelivery()
        delivery.delivery_mode = "Assess"
        delivery.require_grading = 0
        delivery.requires_submission = 1
        delivery.grading_mode = None
        delivery.grade_scale = None
        delivery.task = None
        delivery.rubric_version = "RUBRIC-1"
        delivery.rubric_scoring_strategy = "Separate Criteria"
        delivery._is_quiz_task = Mock(return_value=True)
        delivery._resolve_quiz_max_points = Mock(return_value=12)
        delivery._has_field = Mock(return_value=True)

        delivery._apply_delivery_mode_defaults()

        self.assertEqual(delivery.require_grading, 1)
        self.assertEqual(delivery.requires_submission, 0)
        self.assertEqual(delivery.grading_mode, "Points")
        self.assertEqual(delivery.max_points, 12)
        self.assertIsNone(delivery.rubric_version)
        self.assertIsNone(delivery.rubric_scoring_strategy)

    def test_apply_delivery_mode_defaults_inherits_feedback_flag_from_task_defaults(self):
        task_delivery_service = types.ModuleType("ifitwala_ed.assessment.task_delivery_service")
        task_delivery_service.get_delivery_context = lambda student_group: {}
        task_delivery_service.get_eligible_students = Mock(return_value=[])
        task_delivery_service.bulk_create_outcomes = Mock(return_value=0)

        with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_delivery_service": task_delivery_service}):
            module = import_fresh("ifitwala_ed.assessment.doctype.task_delivery.task_delivery")

        delivery = module.TaskDelivery()
        delivery.delivery_mode = "Collect Work"
        delivery.allow_feedback = None
        delivery._has_field = Mock(
            side_effect=lambda fieldname: fieldname in {"allow_feedback", "allow_late_submission"}
        )
        delivery._get_task_defaults = Mock(return_value={"default_allow_feedback": 1})

        delivery._apply_delivery_mode_defaults()

        self.assertEqual(delivery.allow_feedback, 1)

    def test_validate_class_session_context_rejects_other_student_group(self):
        task_delivery_service = types.ModuleType("ifitwala_ed.assessment.task_delivery_service")
        task_delivery_service.get_delivery_context = lambda student_group: {}
        task_delivery_service.get_eligible_students = Mock(return_value=[])
        task_delivery_service.bulk_create_outcomes = Mock(return_value=0)

        with stubbed_frappe(
            extra_modules={"ifitwala_ed.assessment.task_delivery_service": task_delivery_service}
        ) as frappe:
            frappe.db.get_value = Mock(
                return_value={
                    "name": "CLASS-SESSION-1",
                    "class_teaching_plan": "CLASS-PLAN-1",
                    "student_group": "GROUP-2",
                    "course": "COURSE-1",
                    "academic_year": "AY-2025-2026",
                }
            )
            module = import_fresh("ifitwala_ed.assessment.doctype.task_delivery.task_delivery")

        delivery = module.TaskDelivery()
        delivery.class_teaching_plan = "CLASS-PLAN-1"
        delivery.class_session = "CLASS-SESSION-1"
        delivery.student_group = "GROUP-1"
        delivery.course = "COURSE-1"
        delivery.academic_year = "AY-2025-2026"
        delivery._has_field = Mock(
            side_effect=lambda fieldname: (
                fieldname in {"class_teaching_plan", "class_session", "course", "academic_year"}
            )
        )

        with self.assertRaises(StubValidationError):
            delivery._validate_class_session_context()

    def test_validate_class_teaching_plan_context_rejects_other_student_group(self):
        task_delivery_service = types.ModuleType("ifitwala_ed.assessment.task_delivery_service")
        task_delivery_service.get_delivery_context = lambda student_group: {}
        task_delivery_service.get_eligible_students = Mock(return_value=[])
        task_delivery_service.bulk_create_outcomes = Mock(return_value=0)

        with stubbed_frappe(
            extra_modules={"ifitwala_ed.assessment.task_delivery_service": task_delivery_service}
        ) as frappe:
            frappe.db.get_value = Mock(
                return_value={
                    "name": "CLASS-PLAN-1",
                    "student_group": "GROUP-2",
                    "course": "COURSE-1",
                    "academic_year": "AY-2025-2026",
                    "planning_status": "Active",
                }
            )
            module = import_fresh("ifitwala_ed.assessment.doctype.task_delivery.task_delivery")

        delivery = module.TaskDelivery()
        delivery.class_teaching_plan = "CLASS-PLAN-1"
        delivery.student_group = "GROUP-1"
        delivery.course = "COURSE-1"
        delivery.academic_year = "AY-2025-2026"
        delivery._has_field = Mock(
            side_effect=lambda fieldname: fieldname in {"class_teaching_plan", "course", "academic_year"}
        )

        with self.assertRaises(StubValidationError):
            delivery._validate_class_teaching_plan_context()
