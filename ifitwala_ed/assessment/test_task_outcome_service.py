# ifitwala_ed/assessment/test_task_outcome_service.py

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubPermissionError, StubValidationError, import_fresh, stubbed_frappe


class TestTaskOutcomeService(TestCase):
    def test_points_score_without_grade_scale_omits_null_grade_value_update(self):
        updates = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and fieldname == [
                    "task_delivery",
                    "grade_scale",
                    "is_published",
                ]:
                    return {
                        "task_delivery": "TDL-1",
                        "grade_scale": None,
                        "is_published": 0,
                    }
                if doctype == "Task Outcome" and fieldname == [
                    "official_score",
                    "official_grade",
                    "official_grade_value",
                ]:
                    return {
                        "official_score": None,
                        "official_grade": None,
                        "official_grade_value": None,
                    }
                if doctype == "Task Delivery":
                    return {
                        "grading_mode": "Points",
                        "require_grading": 1,
                        "rubric_scoring_strategy": None,
                        "grade_scale": None,
                        "rubric_version": None,
                    }
                return None

            def fake_get_values(doctype, filters=None, fieldname=None, order_by=None, as_dict=False):
                if doctype == "Task Contribution":
                    return [
                        {
                            "name": "TCO-1",
                            "contribution_type": "Self",
                            "judgment_code": None,
                            "score": 20,
                            "grade": None,
                            "grade_value": None,
                            "feedback": "",
                            "moderation_action": None,
                            "modified": "2026-04-21 11:10:00",
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = fake_get_values
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: updates.append(
                (doctype, name, values, update_modified)
            )

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.apply_official_outcome_from_contributions("OUT-1")

        self.assertEqual(payload, {"outcome": "OUT-1", "grading_status": "Finalized"})
        self.assertEqual(
            updates,
            [
                (
                    "Task Outcome",
                    "OUT-1",
                    {
                        "official_score": 20,
                        "official_grade": None,
                        "official_feedback": "",
                        "grading_status": "Finalized",
                    },
                    True,
                )
            ],
        )

    def test_feedback_only_ungraded_contribution_does_not_write_scalar_fields(self):
        updates = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and fieldname == [
                    "task_delivery",
                    "grade_scale",
                    "is_published",
                ]:
                    return {
                        "task_delivery": "TDL-1",
                        "grade_scale": None,
                        "is_published": 0,
                    }
                if doctype == "Task Delivery":
                    return {
                        "grading_mode": "None",
                        "require_grading": 0,
                        "rubric_scoring_strategy": None,
                        "grade_scale": None,
                        "rubric_version": None,
                    }
                return None

            def fake_get_values(doctype, filters=None, fieldname=None, order_by=None, as_dict=False):
                if doctype == "Task Contribution":
                    return [
                        {
                            "name": "TCO-1",
                            "contribution_type": "Self",
                            "judgment_code": None,
                            "score": None,
                            "grade": None,
                            "grade_value": None,
                            "feedback": "Observation only.",
                            "moderation_action": None,
                            "modified": "2026-04-25 09:10:00",
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = fake_get_values
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: updates.append(
                (doctype, name, values, update_modified)
            )

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.apply_official_outcome_from_contributions("OUT-1")

        self.assertEqual(payload, {"outcome": "OUT-1", "grading_status": "Not Applicable"})
        self.assertEqual(
            updates,
            [
                (
                    "Task Outcome",
                    "OUT-1",
                    {
                        "official_feedback": "Observation only.",
                        "grading_status": "Not Applicable",
                    },
                    True,
                )
            ],
        )

    def test_completion_judgment_contribution_updates_is_complete_without_scalar_writes(self):
        updates = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and fieldname == [
                    "task_delivery",
                    "grade_scale",
                    "is_published",
                ]:
                    return {
                        "task_delivery": "TDL-1",
                        "grade_scale": None,
                        "is_published": 0,
                    }
                if doctype == "Task Delivery":
                    return {
                        "grading_mode": "Completion",
                        "require_grading": 1,
                        "rubric_scoring_strategy": None,
                        "grade_scale": None,
                        "rubric_version": None,
                    }
                if doctype == "Task Outcome" and fieldname == "is_complete":
                    return 0
                return None

            def fake_get_values(doctype, filters=None, fieldname=None, order_by=None, as_dict=False):
                if doctype == "Task Contribution":
                    return [
                        {
                            "name": "TCO-1",
                            "contribution_type": "Self",
                            "judgment_code": "complete",
                            "score": None,
                            "grade": None,
                            "grade_value": None,
                            "feedback": "Observed completion.",
                            "moderation_action": None,
                            "modified": "2026-04-17 17:30:00",
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = fake_get_values
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: updates.append(
                (doctype, name, values, update_modified)
            )

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.apply_official_outcome_from_contributions("OUT-1")

        self.assertEqual(payload, {"outcome": "OUT-1", "grading_status": "Finalized"})
        self.assertEqual(
            updates,
            [
                (
                    "Task Outcome",
                    "OUT-1",
                    {
                        "official_feedback": "Observed completion.",
                        "is_complete": 1,
                        "grading_status": "Finalized",
                    },
                    True,
                )
            ],
        )

    def test_feedback_only_completion_contribution_preserves_current_is_complete(self):
        updates = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and fieldname == [
                    "task_delivery",
                    "grade_scale",
                    "is_published",
                ]:
                    return {
                        "task_delivery": "TDL-1",
                        "grade_scale": None,
                        "is_published": 0,
                    }
                if doctype == "Task Delivery":
                    return {
                        "grading_mode": "Completion",
                        "require_grading": 1,
                        "rubric_scoring_strategy": None,
                        "grade_scale": None,
                        "rubric_version": None,
                    }
                if doctype == "Task Outcome" and fieldname == "is_complete":
                    return 1
                return None

            def fake_get_values(doctype, filters=None, fieldname=None, order_by=None, as_dict=False):
                if doctype == "Task Contribution":
                    return [
                        {
                            "name": "TCO-1",
                            "contribution_type": "Self",
                            "judgment_code": None,
                            "score": None,
                            "grade": None,
                            "grade_value": None,
                            "feedback": "Comment only refresh.",
                            "moderation_action": None,
                            "modified": "2026-04-17 17:35:00",
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = fake_get_values
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: updates.append(
                (doctype, name, values, update_modified)
            )

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.apply_official_outcome_from_contributions("OUT-1")

        self.assertEqual(payload, {"outcome": "OUT-1", "grading_status": "Finalized"})
        self.assertEqual(
            updates,
            [
                (
                    "Task Outcome",
                    "OUT-1",
                    {
                        "official_feedback": "Comment only refresh.",
                        "is_complete": 1,
                        "grading_status": "Finalized",
                    },
                    True,
                )
            ],
        )

    def test_missing_boolean_contributions_reset_is_complete(self):
        updates = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and fieldname == [
                    "task_delivery",
                    "grade_scale",
                    "is_published",
                ]:
                    return {
                        "task_delivery": "TDL-1",
                        "grade_scale": None,
                        "is_published": 0,
                    }
                if doctype == "Task Delivery":
                    return {
                        "grading_mode": "Binary",
                        "require_grading": 1,
                        "rubric_scoring_strategy": None,
                        "grade_scale": None,
                        "rubric_version": None,
                    }
                return None

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = lambda *args, **kwargs: []
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: updates.append(
                (doctype, name, values, update_modified)
            )

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.apply_official_outcome_from_contributions("OUT-1")

        self.assertEqual(payload, {"outcome": "OUT-1", "grading_status": "Not Started"})
        self.assertEqual(
            updates,
            [
                (
                    "Task Outcome",
                    "OUT-1",
                    {
                        "official_feedback": None,
                        "is_complete": 0,
                        "grading_status": "Not Started",
                    },
                    True,
                )
            ],
        )

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
                            "judgment_code": None,
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

    def test_criteria_sum_total_uses_weighted_local_max_points(self):
        updates = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and fieldname == [
                    "task_delivery",
                    "grade_scale",
                    "is_published",
                ]:
                    return {
                        "task_delivery": "TDL-1",
                        "grade_scale": None,
                        "is_published": 0,
                    }
                if doctype == "Task Delivery":
                    return {
                        "grading_mode": "Criteria",
                        "require_grading": 1,
                        "rubric_scoring_strategy": "Sum Total",
                        "grade_scale": None,
                        "rubric_version": "TRV-1",
                    }
                return None

            def fake_get_values(doctype, filters=None, fieldname=None, order_by=None, as_dict=False):
                if doctype == "Task Contribution":
                    return [
                        {
                            "name": "TCO-1",
                            "contribution_type": "Self",
                            "judgment_code": None,
                            "score": None,
                            "grade": None,
                            "grade_value": None,
                            "feedback": "Strong evidence.",
                            "moderation_action": None,
                            "modified": "2026-04-18 09:30:00",
                        }
                    ]
                if doctype == "Task Contribution Criterion":
                    return [
                        {
                            "assessment_criteria": "CRIT-ANALYSIS",
                            "level": "6",
                            "level_points": 6,
                            "feedback": "Analysis is clear.",
                        },
                        {
                            "assessment_criteria": "CRIT-COMMUNICATION",
                            "level": "9",
                            "level_points": 9,
                            "feedback": "Communication is strong.",
                        },
                    ]
                if doctype == "Task Rubric Criterion":
                    return [
                        {
                            "assessment_criteria": "CRIT-ANALYSIS",
                            "criteria_weighting": 40,
                            "criteria_max_points": 8,
                        },
                        {
                            "assessment_criteria": "CRIT-COMMUNICATION",
                            "criteria_weighting": 60,
                            "criteria_max_points": 10,
                        },
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = fake_get_values
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: updates.append(
                (doctype, name, values, update_modified)
            )
            frappe.db.delete = lambda *args, **kwargs: None
            frappe.db.bulk_insert = lambda *args, **kwargs: None
            frappe.generate_hash = lambda length=10: "HASHEDROW"

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.apply_official_outcome_from_contributions("OUT-1")

        self.assertEqual(payload, {"outcome": "OUT-1", "grading_status": "Finalized"})
        self.assertEqual(
            updates[-1],
            (
                "Task Outcome",
                "OUT-1",
                {
                    "official_score": 84.0,
                    "official_grade": None,
                    "official_feedback": "Strong evidence.",
                    "grading_status": "Finalized",
                },
                True,
            ),
        )

    def test_criteria_sum_total_preserves_legacy_weight_multipliers_when_weights_are_not_percentages(self):
        updates = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and fieldname == [
                    "task_delivery",
                    "grade_scale",
                    "is_published",
                ]:
                    return {
                        "task_delivery": "TDL-1",
                        "grade_scale": None,
                        "is_published": 0,
                    }
                if doctype == "Task Delivery":
                    return {
                        "grading_mode": "Criteria",
                        "require_grading": 1,
                        "rubric_scoring_strategy": "Sum Total",
                        "grade_scale": None,
                        "rubric_version": "TRV-1",
                    }
                return None

            def fake_get_values(doctype, filters=None, fieldname=None, order_by=None, as_dict=False):
                if doctype == "Task Contribution":
                    return [
                        {
                            "name": "TCO-1",
                            "contribution_type": "Self",
                            "judgment_code": None,
                            "score": None,
                            "grade": None,
                            "grade_value": None,
                            "feedback": "Legacy rubric payload.",
                            "moderation_action": None,
                            "modified": "2026-04-18 09:30:00",
                        }
                    ]
                if doctype == "Task Contribution Criterion":
                    return [
                        {
                            "assessment_criteria": "CRIT-ANALYSIS",
                            "level": "4",
                            "level_points": 4,
                            "feedback": None,
                        },
                        {
                            "assessment_criteria": "CRIT-COMMUNICATION",
                            "level": "3",
                            "level_points": 3,
                            "feedback": None,
                        },
                    ]
                if doctype == "Task Rubric Criterion":
                    return [
                        {
                            "assessment_criteria": "CRIT-ANALYSIS",
                            "criteria_weighting": 1,
                            "criteria_max_points": 8,
                        },
                        {
                            "assessment_criteria": "CRIT-COMMUNICATION",
                            "criteria_weighting": 2,
                            "criteria_max_points": 10,
                        },
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = fake_get_values
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: updates.append(
                (doctype, name, values, update_modified)
            )
            frappe.db.delete = lambda *args, **kwargs: None
            frappe.db.bulk_insert = lambda *args, **kwargs: None
            frappe.generate_hash = lambda length=10: "HASHEDROW"

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.apply_official_outcome_from_contributions("OUT-1")

        self.assertEqual(payload, {"outcome": "OUT-1", "grading_status": "Finalized"})
        self.assertEqual(updates[-1][2]["official_score"], 10.0)

    def test_set_assign_only_completion_stamps_completed_on(self):
        saves = []

        class _FakeOutcomeDoc:
            def __init__(self):
                self.name = "OUT-1"
                self.is_complete = 0
                self.completed_on = None

            def save(self, ignore_permissions=False):
                saves.append(
                    {
                        "is_complete": self.is_complete,
                        "completed_on": self.completed_on,
                        "ignore_permissions": ignore_permissions,
                    }
                )

        with stubbed_frappe() as frappe:
            frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: (
                {
                    "name": "OUT-1",
                    "task_delivery": "TDL-1",
                    "student": "STU-1",
                    "is_published": 0,
                    "is_complete": 0,
                    "completed_on": None,
                }
                if doctype == "Task Outcome"
                else {
                    "delivery_mode": "Assign Only",
                    "grading_mode": "Completion",
                    "require_grading": 0,
                    "rubric_scoring_strategy": None,
                    "grade_scale": None,
                    "rubric_version": None,
                }
            )
            frappe.get_doc = lambda doctype, name: _FakeOutcomeDoc()

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.set_assign_only_completion("OUT-1", is_complete=1, ignore_permissions=True)

        self.assertEqual(payload["outcome"], "OUT-1")
        self.assertEqual(payload["is_complete"], 1)
        self.assertEqual(payload["completed_on"], "2026-03-12 17:45:04")
        self.assertEqual(
            saves,
            [
                {
                    "is_complete": 1,
                    "completed_on": "2026-03-12 17:45:04",
                    "ignore_permissions": True,
                }
            ],
        )

    def test_set_assign_only_completion_is_idempotent_when_already_complete(self):
        with stubbed_frappe() as frappe:
            frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: (
                {
                    "name": "OUT-1",
                    "task_delivery": "TDL-1",
                    "student": "STU-1",
                    "is_published": 0,
                    "is_complete": 1,
                    "completed_on": "2026-04-20 09:30:00",
                }
                if doctype == "Task Outcome"
                else {
                    "delivery_mode": "Assign Only",
                    "grading_mode": "Completion",
                    "require_grading": 0,
                    "rubric_scoring_strategy": None,
                    "grade_scale": None,
                    "rubric_version": None,
                }
            )
            frappe.get_doc = lambda doctype, name: (_ for _ in ()).throw(AssertionError("save should not be called"))

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            payload = module.set_assign_only_completion("OUT-1", is_complete=1)

        self.assertEqual(
            payload,
            {
                "outcome": "OUT-1",
                "is_complete": 1,
                "completed_on": "2026-04-20 09:30:00",
            },
        )

    def test_set_assign_only_completion_rejects_published_outcomes(self):
        task_feedback_service = types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
        task_feedback_service.build_publication_state_map = lambda outcome_ids: {
            outcome_id: {"is_visible_to_any_audience": True} for outcome_id in outcome_ids or []
        }

        with stubbed_frappe(
            extra_modules={"ifitwala_ed.assessment.task_feedback_service": task_feedback_service}
        ) as frappe:
            frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: (
                {
                    "name": "OUT-1",
                    "task_delivery": "TDL-1",
                    "student": "STU-1",
                    "is_published": 1,
                    "is_complete": 1,
                    "completed_on": "2026-04-20 09:30:00",
                }
                if doctype == "Task Outcome"
                else {
                    "delivery_mode": "Assign Only",
                    "grading_mode": "Completion",
                    "require_grading": 0,
                    "rubric_scoring_strategy": None,
                    "grade_scale": None,
                    "rubric_version": None,
                }
            )

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            with self.assertRaises(StubValidationError):
                module.set_assign_only_completion("OUT-1", is_complete=1)

    def test_set_assign_only_completion_rejects_student_mismatch(self):
        with stubbed_frappe() as frappe:
            frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: (
                {
                    "name": "OUT-1",
                    "task_delivery": "TDL-1",
                    "student": "STU-2",
                    "is_published": 0,
                    "is_complete": 0,
                    "completed_on": None,
                }
                if doctype == "Task Outcome"
                else {
                    "delivery_mode": "Assign Only",
                    "grading_mode": "Completion",
                    "require_grading": 0,
                    "rubric_scoring_strategy": None,
                    "grade_scale": None,
                    "rubric_version": None,
                }
            )

            module = import_fresh("ifitwala_ed.assessment.task_outcome_service")
            with self.assertRaises(StubPermissionError):
                module.set_assign_only_completion("OUT-1", is_complete=1, expected_student="STU-1")
