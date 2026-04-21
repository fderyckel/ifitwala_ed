# ifitwala_ed/assessment/test_task_delivery_service.py

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _planning_stub(resolve_active_class_teaching_plan=None):
    module = types.ModuleType("ifitwala_ed.curriculum.planning")
    module.resolve_active_class_teaching_plan = resolve_active_class_teaching_plan or (lambda student_group: {})
    return module


class TestTaskDeliveryService(TestCase):
    def test_get_eligible_students_uses_supported_pluck_query(self):
        captured: dict[str, object] = {}

        with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.planning": _planning_stub()}) as frappe:

            def fake_get_all(doctype, **kwargs):
                captured["doctype"] = doctype
                captured["kwargs"] = kwargs
                return ["STU-1", "STU-2"]

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.assessment.task_delivery_service")
            students = module.get_eligible_students("GRP-1")

        self.assertEqual(students, ["STU-1", "STU-2"])
        self.assertEqual(captured["doctype"], "Student Group Student")
        self.assertEqual(
            captured["kwargs"],
            {
                "filters": {
                    "parent": "GRP-1",
                    "parenttype": "Student Group",
                    "active": 1,
                },
                "pluck": "student",
                "limit": 0,
            },
        )

    def test_resolve_planning_context_uses_active_class_plan_when_missing(self):
        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.curriculum.planning": _planning_stub(
                    lambda student_group: {
                        "status": "ready",
                        "class_teaching_plan": "CLASS-PLAN-1",
                        "active_plan_count": 1,
                    }
                )
            }
        ) as frappe:
            frappe.db.get_value = lambda doctype, name, fields=None, as_dict=False: {
                "name": "CLASS-PLAN-1",
                "student_group": "GRP-1",
                "course_plan": "COURSE-PLAN-1",
                "course": "COURSE-1",
                "academic_year": "AY-2025-2026",
                "planning_status": "Active",
            }

            module = import_fresh("ifitwala_ed.assessment.task_delivery_service")
            context = module.resolve_planning_context("GRP-1")

        self.assertEqual(context["class_teaching_plan"], "CLASS-PLAN-1")
        self.assertEqual(context["course_plan"], "COURSE-PLAN-1")

    def test_resolve_planning_context_rejects_explicit_non_active_class_plan(self):
        with stubbed_frappe(extra_modules={"ifitwala_ed.curriculum.planning": _planning_stub()}) as frappe:
            frappe.db.get_value = lambda doctype, name, fields=None, as_dict=False: {
                "name": "CLASS-PLAN-1",
                "student_group": "GRP-1",
                "course_plan": "COURSE-PLAN-1",
                "course": "COURSE-1",
                "academic_year": "AY-2025-2026",
                "planning_status": "Draft",
            }

            module = import_fresh("ifitwala_ed.assessment.task_delivery_service")

            with self.assertRaisesRegex(
                Exception,
                "This class needs an active Class Teaching Plan before assigned work can be created.",
            ):
                module.resolve_planning_context("GRP-1", class_teaching_plan="CLASS-PLAN-1")
