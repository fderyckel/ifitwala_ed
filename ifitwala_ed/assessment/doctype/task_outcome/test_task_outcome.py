# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _import_task_outcome_module():
    task_outcome_service = types.ModuleType("ifitwala_ed.assessment.task_outcome_service")
    task_outcome_service.resolve_grade_symbol = lambda *_args, **_kwargs: 1

    with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_outcome_service": task_outcome_service}):
        return import_fresh("ifitwala_ed.assessment.doctype.task_outcome.task_outcome")


class TestTaskOutcome(TestCase):
    def test_unique_index_exists_matches_ordered_columns(self):
        module = _import_task_outcome_module()
        rows = [
            {
                "Key_name": "uniq_task_outcome_delivery_student",
                "Non_unique": 0,
                "Seq_in_index": 1,
                "Column_name": "task_delivery",
            },
            {
                "Key_name": "uniq_task_outcome_delivery_student",
                "Non_unique": 0,
                "Seq_in_index": 2,
                "Column_name": "student",
            },
        ]

        self.assertTrue(module._unique_index_exists(rows, ["task_delivery", "student"]))

    def test_unique_index_exists_ignores_non_unique_index(self):
        module = _import_task_outcome_module()
        rows = [
            {
                "Key_name": "idx_task_outcome_delivery_student",
                "Non_unique": 1,
                "Seq_in_index": 1,
                "Column_name": "task_delivery",
            },
            {
                "Key_name": "idx_task_outcome_delivery_student",
                "Non_unique": 1,
                "Seq_in_index": 2,
                "Column_name": "student",
            },
        ]

        self.assertFalse(module._unique_index_exists(rows, ["task_delivery", "student"]))

    def test_backfill_denorm_fields_reads_missing_required_and_optional_fields(self):
        task_outcome_service = types.ModuleType("ifitwala_ed.assessment.task_outcome_service")
        task_outcome_service.resolve_grade_symbol = lambda *_args, **_kwargs: 1

        with stubbed_frappe(
            extra_modules={"ifitwala_ed.assessment.task_outcome_service": task_outcome_service}
        ) as frappe:
            captured: dict[str, object] = {}

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                captured["doctype"] = doctype
                captured["name"] = name
                captured["fieldname"] = fieldname
                captured["as_dict"] = as_dict
                return {
                    "task": "TASK-1",
                    "course": "COURSE-1",
                    "grade_scale": "GRADE-SCALE-1",
                }

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.assessment.doctype.task_outcome.task_outcome")
            outcome = module.TaskOutcome()
            outcome.doctype = "Task Outcome"
            outcome.task_delivery = "TDL-1"
            outcome.student = "STU-1"
            outcome.task = None
            outcome.student_group = "GRP-1"
            outcome.course = None
            outcome.academic_year = "AY-2025-2026"
            outcome.school = "SCHOOL-1"

            outcome._backfill_denorm_fields()

        self.assertEqual(captured["doctype"], "Task Delivery")
        self.assertEqual(captured["name"], "TDL-1")
        self.assertEqual(captured["fieldname"], ["task", "course", "grade_scale"])
        self.assertTrue(captured["as_dict"])
        self.assertEqual(outcome.task, "TASK-1")
        self.assertEqual(outcome.course, "COURSE-1")
        self.assertEqual(outcome.grade_scale, "GRADE-SCALE-1")
