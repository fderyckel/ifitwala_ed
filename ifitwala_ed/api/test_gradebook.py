# ifitwala_ed/api/test_gradebook.py

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeDelivery:
    def __init__(self):
        self.name = "TDL-0001"
        self.student_group = "GRP-1"
        self.docstatus = 0
        self.flags = types.SimpleNamespace(ignore_permissions=False)
        self.submit_calls = 0
        self.materialize_calls = 0
        self.outcome_count = 0

    def submit(self):
        self.submit_calls += 1
        self.docstatus = 1

    def materialize_roster(self):
        self.materialize_calls += 1
        self.outcome_count = 3
        return {"eligible_students": 3, "outcomes_created": 3}


class TestGradebookApi(TestCase):
    def test_repair_task_roster_submits_draft_delivery_and_backfills_outcomes(self):
        delivery = _FakeDelivery()

        stub_services = {
            "ifitwala_ed.assessment.task_contribution_service": types.ModuleType(
                "ifitwala_ed.assessment.task_contribution_service"
            ),
            "ifitwala_ed.assessment.task_outcome_service": types.ModuleType(
                "ifitwala_ed.assessment.task_outcome_service"
            ),
            "ifitwala_ed.assessment.task_submission_service": types.ModuleType(
                "ifitwala_ed.assessment.task_submission_service"
            ),
        }

        with stubbed_frappe(extra_modules=stub_services) as frappe:
            frappe.db.count = lambda doctype, filters=None: delivery.outcome_count
            frappe.get_doc = lambda doctype, name: delivery

            module = import_fresh("ifitwala_ed.api.gradebook")
            module._can_write_gradebook = lambda: True
            module._assert_group_access = lambda student_group: None

            payload = module.repair_task_roster("TDL-0001")

        self.assertEqual(delivery.submit_calls, 1)
        self.assertTrue(delivery.flags.ignore_permissions)
        self.assertEqual(delivery.materialize_calls, 1)
        self.assertEqual(
            payload,
            {
                "task_delivery": "TDL-0001",
                "docstatus": 1,
                "was_draft": 1,
                "eligible_students": 3,
                "outcomes_created": 3,
                "outcomes_total": 3,
                "message": "Roster synced for 3 students.",
            },
        )
