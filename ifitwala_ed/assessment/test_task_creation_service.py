# ifitwala_ed/assessment/test_task_creation_service.py

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _MetaField:
    def __init__(self, options: str):
        self.options = options


class _Meta:
    def __init__(self, fields: dict[str, str]):
        self._fields = fields

    def get_field(self, fieldname: str):
        options = self._fields.get(fieldname)
        if options is None:
            return None
        return _MetaField(options)


class _FakeTask:
    def __init__(self):
        self.name = "TASK-0001"
        self.insert_calls = 0
        self.unit_plan = None
        self.lesson = None

    def insert(self):
        self.insert_calls += 1


class _FakeDelivery:
    def __init__(self):
        self.name = "TDL-0001"
        self.flags = types.SimpleNamespace(ignore_permissions=False)
        self.insert_calls: list[bool] = []
        self.submit_calls = 0
        self.materialize_calls = 0

    def insert(self, ignore_permissions=False):
        self.insert_calls.append(ignore_permissions)

    def submit(self):
        self.submit_calls += 1

    def materialize_roster(self):
        self.materialize_calls += 1
        return {"eligible_students": 3, "outcomes_created": 3}


class TestTaskCreationService(TestCase):
    def test_create_task_and_delivery_submits_and_materializes_delivery(self):
        task = _FakeTask()
        delivery = _FakeDelivery()
        created_docs = [task, delivery]

        with stubbed_frappe() as frappe:
            frappe.db.savepoint = lambda name: None
            frappe.db.rollback = lambda save_point=None: None

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Student Group":
                    return "COURSE-1"
                if doctype == "Class Teaching Plan":
                    return {
                        "name": "CLASS-PLAN-1",
                        "student_group": "GRP-1",
                        "course_plan": "COURSE-PLAN-1",
                        "course": "COURSE-1",
                        "academic_year": "AY-2025-2026",
                        "planning_status": "Active",
                    }
                return "COURSE-1"

            frappe.db.get_value = fake_get_value
            frappe.db.count = lambda doctype, filters=None: 3
            frappe.get_all = lambda doctype, **kwargs: (
                [{"name": "CLASS-PLAN-1"}] if doctype == "Class Teaching Plan" else []
            )
            frappe.get_meta = lambda doctype: {
                "Task": _Meta({"task_type": "Homework\nQuiz"}),
                "Task Delivery": _Meta({"delivery_mode": "Assign Only\nCollect Work\nAssess"}),
            }[doctype]
            frappe.new_doc = lambda doctype: created_docs.pop(0)

            module = import_fresh("ifitwala_ed.assessment.task_creation_service")

            payload = module.create_task_and_delivery(
                title="Homework 11",
                student_group="GRP-1",
                class_teaching_plan="CLASS-PLAN-1",
                unit_plan="UNIT-1",
                lesson="LESSON-1",
                delivery_mode="Assess",
                grading_mode="Points",
                allow_feedback="1",
                max_points="20",
                allow_late_submission="1",
                group_submission="0",
            )

        self.assertEqual(task.insert_calls, 1)
        self.assertEqual(task.unit_plan, "UNIT-1")
        self.assertEqual(task.lesson, "LESSON-1")
        self.assertEqual(task.default_allow_feedback, 1)
        self.assertEqual(delivery.task, "TASK-0001")
        self.assertEqual(delivery.student_group, "GRP-1")
        self.assertEqual(delivery.class_teaching_plan, "CLASS-PLAN-1")
        self.assertEqual(delivery.group_submission, 0)
        self.assertEqual(delivery.allow_late_submission, 1)
        self.assertEqual(delivery.allow_feedback, 1)
        self.assertEqual(delivery.insert_calls, [True])
        self.assertTrue(delivery.flags.ignore_permissions)
        self.assertEqual(delivery.submit_calls, 1)
        self.assertEqual(delivery.materialize_calls, 1)
        self.assertEqual(
            payload,
            {
                "task": "TASK-0001",
                "task_delivery": "TDL-0001",
                "outcomes_created": 3,
            },
        )
