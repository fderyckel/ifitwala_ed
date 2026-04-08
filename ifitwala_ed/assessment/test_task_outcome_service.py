# ifitwala_ed/assessment/test_task_outcome_service.py

from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestTaskOutcomeService(TestCase):
    def test_criteria_feedback_only_contribution_preserves_existing_rubric_fields(self):
        updates = []
        delete_calls = []
        bulk_insert_calls = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and fieldname == [
                    "task_delivery",
                    "grade_scale",
                    "is_published",
                ]:
                    return {
                        "task_delivery": "TDL-1",
                        "grade_scale": "SCALE-1",
                        "is_published": 0,
                    }
                if doctype == "Task Delivery":
                    return {
                        "grading_mode": "Criteria",
                        "require_grading": 1,
                        "rubric_scoring_strategy": "Sum Total",
                        "grade_scale": "SCALE-1",
                        "rubric_version": "TRV-1",
                    }
                if doctype == "Task Outcome" and fieldname == [
                    "official_score",
                    "official_grade",
                    "official_grade_value",
                ]:
                    return {
                        "official_score": 6.5,
                        "official_grade": "B",
                        "official_grade_value": 3.0,
                    }
                return None

            def fake_get_values(doctype, filters=None, fieldname=None, order_by=None, as_dict=False):
                if doctype == "Task Contribution":
                    return [
                        {
                            "name": "TCO-1",
                            "contribution_type": "Self",
                            "score": None,
                            "grade": None,
                            "grade_value": None,
                            "feedback": "Refine argument.",
                            "moderation_action": None,
                            "modified": "2026-04-02 18:35:00",
                        }
                    ]
                if doctype == "Task Contribution Criterion":
                    return []
                return []

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = fake_get_values
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: updates.append(
                (doctype, name, values, update_modified)
            )
            frappe.db.delete = lambda *args, **kwargs: delete_calls.append((args, kwargs))
            frappe.db.bulk_insert = lambda *args, **kwargs: bulk_insert_calls.append((args, kwargs))

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")

            payload = module.apply_official_outcome_from_contributions("OUT-1")

        self.assertEqual(payload, {"outcome": "OUT-1", "grading_status": "Finalized"})
        self.assertEqual(delete_calls, [])
        self.assertEqual(bulk_insert_calls, [])
        self.assertEqual(
            updates,
            [
                (
                    "Task Outcome",
                    "OUT-1",
                    {
                        "official_score": 6.5,
                        "official_grade": "B",
                        "official_grade_value": 3.0,
                        "official_feedback": "Refine argument.",
                        "grading_status": "Finalized",
                    },
                    True,
                )
            ],
        )
