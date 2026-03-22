# ifitwala_ed/assessment/test_task_delivery_service.py

from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestTaskDeliveryService(TestCase):
    def test_get_eligible_students_uses_supported_pluck_query(self):
        captured: dict[str, object] = {}

        with stubbed_frappe() as frappe:

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
