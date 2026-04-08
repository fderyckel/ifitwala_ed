# ifitwala_ed/api/test_gradebook.py

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


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


def _gradebook_stub_modules(task_contribution_service=None):
    image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils.apply_preferred_student_images = lambda rows: rows

    return {
        "ifitwala_ed.assessment.task_contribution_service": task_contribution_service
        or types.ModuleType("ifitwala_ed.assessment.task_contribution_service"),
        "ifitwala_ed.assessment.task_outcome_service": types.ModuleType("ifitwala_ed.assessment.task_outcome_service"),
        "ifitwala_ed.assessment.task_submission_service": types.ModuleType(
            "ifitwala_ed.assessment.task_submission_service"
        ),
        "ifitwala_ed.utilities.image_utils": image_utils,
    }


class TestGradebookApi(TestCase):
    def test_repair_task_roster_submits_draft_delivery_and_backfills_outcomes(self):
        delivery = _FakeDelivery()

        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:
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

    def test_fetch_group_tasks_exposes_grading_mode_and_comment_flag(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0):
                if doctype == "Task Delivery":
                    return [
                        {
                            "name": "TDL-0001",
                            "task": "TASK-1",
                            "due_date": "2026-04-03 10:00:00",
                            "delivery_mode": "Assess",
                            "grading_mode": "Criteria",
                            "allow_feedback": 1,
                            "max_points": None,
                            "rubric_scoring_strategy": "Separate Criteria",
                        }
                    ]
                if doctype == "Task":
                    return [{"name": "TASK-1", "title": "Rubric reflection", "task_type": "Assignment"}]
                return []

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.gradebook")
            module._can_read_gradebook = lambda: True
            module._assert_group_access = lambda student_group: None

            payload = module.fetch_group_tasks("GRP-1")

        self.assertEqual(
            payload,
            {
                "tasks": [
                    {
                        "name": "TDL-0001",
                        "title": "Rubric reflection",
                        "due_date": "2026-04-03 10:00:00",
                        "status": None,
                        "grading_mode": "Criteria",
                        "allow_feedback": 1,
                        "rubric_scoring_strategy": "Separate Criteria",
                        "points": 0,
                        "binary": 0,
                        "criteria": 1,
                        "observations": 0,
                        "max_points": None,
                        "task_type": "Assignment",
                        "delivery_type": "Assess",
                    }
                ]
            },
        )

    def test_update_task_student_rejects_feedback_when_comments_disabled(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    return {"name": "OUT-1", "task_delivery": "TDL-1", "official_score": None}
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 0,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.api.gradebook")
            module._can_write_gradebook = lambda: True
            module._assert_group_access = lambda student_group: None

            with self.assertRaises(StubValidationError):
                module.update_task_student("OUT-1", {"feedback": "Needs a stronger explanation."})

    def test_update_task_student_allows_criteria_comment_before_any_rubric_score(self):
        submitted_payloads = []

        task_contribution_service = types.ModuleType("ifitwala_ed.assessment.task_contribution_service")
        task_contribution_service.submit_contribution = lambda payload, contributor=None: (
            submitted_payloads.append((payload, contributor)) or {"contribution": "TCO-1"}
        )

        with stubbed_frappe(
            extra_modules=_gradebook_stub_modules(task_contribution_service=task_contribution_service)
        ) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    if fieldname == ["name", "task_delivery", "official_score"]:
                        return {"name": "OUT-1", "task_delivery": "TDL-1", "official_score": None}
                    return {
                        "name": "OUT-1",
                        "official_score": None,
                        "official_feedback": "Focus on examples.",
                        "grading_status": "Not Started",
                        "is_complete": 0,
                        "is_published": 0,
                        "modified": "2026-04-02 18:30:00",
                    }
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Criteria",
                        "allow_feedback": 1,
                    }
                return None

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = lambda *args, **kwargs: []

            module = import_fresh("ifitwala_ed.api.gradebook")
            module._can_write_gradebook = lambda: True
            module._assert_group_access = lambda student_group: None
            module._resolve_or_create_stub_submission_id = lambda task_student, payload: "SUB-1"

            payload = module.update_task_student("OUT-1", {"feedback": "Focus on examples."})

        self.assertEqual(
            submitted_payloads,
            [
                (
                    {
                        "task_outcome": "OUT-1",
                        "feedback": "Focus on examples.",
                        "task_submission": "SUB-1",
                    },
                    "unit.test@example.com",
                )
            ],
        )
        self.assertEqual(payload["feedback"], "Focus on examples.")
