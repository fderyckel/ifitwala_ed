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
    quiz_service = types.ModuleType("ifitwala_ed.assessment.quiz_service")
    quiz_service.MANUAL_TYPES = {"Essay"}
    quiz_service.refresh_attempt = lambda *args, **kwargs: {"attempt": {"name": args[0] if args else "QAT-1"}}

    return {
        "ifitwala_ed.assessment.quiz_service": quiz_service,
        "ifitwala_ed.assessment.task_contribution_service": task_contribution_service
        or types.ModuleType("ifitwala_ed.assessment.task_contribution_service"),
        "ifitwala_ed.assessment.task_outcome_service": types.ModuleType("ifitwala_ed.assessment.task_outcome_service"),
        "ifitwala_ed.assessment.task_submission_service": types.ModuleType(
            "ifitwala_ed.assessment.task_submission_service"
        ),
        "ifitwala_ed.utilities.image_utils": image_utils,
    }


class TestGradebookApi(TestCase):
    def test_get_task_quiz_manual_review_groups_manual_rows_by_question(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "task": "TASK-QUIZ-1",
                        "student_group": "GRP-1",
                        "due_date": "2026-04-08 10:00:00",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 0,
                        "max_points": 4,
                        "rubric_version": None,
                        "rubric_scoring_strategy": None,
                        "quiz_pass_percentage": 75,
                    }
                if doctype == "Task":
                    return {"name": "TASK-QUIZ-1", "title": "Unit Reflection Quiz", "task_type": "Quiz"}
                return None

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Outcome":
                    return [
                        {"name": "OUT-1", "student": "STU-1", "grading_status": "Needs Review"},
                        {"name": "OUT-2", "student": "STU-2", "grading_status": "Finalized"},
                    ]
                if doctype == "Quiz Attempt":
                    return [
                        {
                            "name": "QAT-1",
                            "task_outcome": "OUT-1",
                            "student": "STU-1",
                            "attempt_number": 1,
                            "status": "Needs Review",
                            "submitted_on": "2026-04-08 10:15:00",
                            "score": None,
                            "percentage": None,
                            "passed": 0,
                            "requires_manual_review": 1,
                        },
                        {
                            "name": "QAT-2",
                            "task_outcome": "OUT-2",
                            "student": "STU-2",
                            "attempt_number": 1,
                            "status": "Submitted",
                            "submitted_on": "2026-04-08 10:25:00",
                            "score": 4,
                            "percentage": 100,
                            "passed": 1,
                            "requires_manual_review": 0,
                        },
                    ]
                if doctype == "Quiz Attempt Item":
                    return [
                        {
                            "name": "QAI-1",
                            "quiz_attempt": "QAT-1",
                            "quiz_question": "QQ-1",
                            "position": 1,
                            "question_type": "Essay",
                            "prompt_html": "<p>Explain your reasoning.</p>",
                            "option_payload": None,
                            "response_text": "Student one response",
                            "response_payload": None,
                            "awarded_score": None,
                            "requires_manual_grading": 1,
                        },
                        {
                            "name": "QAI-2",
                            "quiz_attempt": "QAT-2",
                            "quiz_question": "QQ-1",
                            "position": 1,
                            "question_type": "Essay",
                            "prompt_html": "<p>Explain your reasoning.</p>",
                            "option_payload": None,
                            "response_text": "Student two response",
                            "response_payload": None,
                            "awarded_score": 1,
                            "requires_manual_grading": 0,
                        },
                    ]
                if doctype == "Quiz Question":
                    return [{"name": "QQ-1", "title": "Explain the pattern"}]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.gradebook")
            module._can_read_gradebook = lambda: True
            module._assert_group_access = lambda student_group: None
            module._get_student_display_map = lambda student_ids: {
                "STU-1": "Ada Lovelace",
                "STU-2": "Grace Hopper",
            }
            module._get_student_meta_map = lambda student_ids: {
                "STU-1": {"name": "STU-1", "student_id": "S-001", "student_image": None},
                "STU-2": {"name": "STU-2", "student_id": "S-002", "student_image": None},
            }

            payload = module.get_task_quiz_manual_review("TDL-1", view_mode="question")

        self.assertEqual(payload["task"]["title"], "Unit Reflection Quiz")
        self.assertEqual(payload["summary"]["manual_item_count"], 2)
        self.assertEqual(payload["summary"]["pending_item_count"], 1)
        self.assertEqual(payload["view_mode"], "question")
        self.assertEqual(payload["selected_question"], {"quiz_question": "QQ-1", "title": "Explain the pattern"})
        self.assertEqual([row["student_name"] for row in payload["rows"]], ["Ada Lovelace", "Grace Hopper"])
        self.assertEqual(payload["rows"][0]["requires_manual_grading"], 1)
        self.assertEqual(payload["rows"][1]["awarded_score"], 1.0)

    def test_save_task_quiz_manual_review_updates_items_and_refreshes_attempts(self):
        set_value_calls = []
        refresh_calls = []
        modules = _gradebook_stub_modules()
        modules["ifitwala_ed.assessment.quiz_service"].refresh_attempt = lambda attempt_id, **kwargs: (
            refresh_calls.append((attempt_id, kwargs)) or {"attempt": {"name": attempt_id}}
        )

        with stubbed_frappe(extra_modules=modules) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "task": "TASK-QUIZ-1",
                        "student_group": "GRP-1",
                        "due_date": "2026-04-08 10:00:00",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 0,
                        "max_points": 4,
                        "rubric_version": None,
                        "rubric_scoring_strategy": None,
                    }
                if doctype == "Task":
                    return {"name": "TASK-QUIZ-1", "title": "Unit Reflection Quiz", "task_type": "Quiz"}
                return None

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Quiz Attempt Item":
                    return [
                        {"name": "QAI-1", "quiz_attempt": "QAT-1", "question_type": "Essay"},
                        {"name": "QAI-2", "quiz_attempt": "QAT-2", "question_type": "Essay"},
                    ]
                if doctype == "Quiz Attempt":
                    return [
                        {
                            "name": "QAT-1",
                            "task_delivery": "TDL-1",
                            "student": "STU-1",
                            "status": "Needs Review",
                        },
                        {
                            "name": "QAT-2",
                            "task_delivery": "TDL-1",
                            "student": "STU-2",
                            "status": "Submitted",
                        },
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: set_value_calls.append(
                (doctype, name, values, update_modified)
            )

            module = import_fresh("ifitwala_ed.api.gradebook")
            module._can_write_gradebook = lambda: True
            module._assert_group_access = lambda student_group: None

            payload = module.save_task_quiz_manual_review(
                "TDL-1",
                grades=[
                    {"item_id": "QAI-1", "awarded_score": 1},
                    {"item_id": "QAI-2", "awarded_score": 0.5},
                ],
            )

        self.assertEqual(
            set_value_calls,
            [
                ("Quiz Attempt Item", "QAI-1", {"awarded_score": 1.0}, True),
                ("Quiz Attempt Item", "QAI-2", {"awarded_score": 0.5}, True),
            ],
        )
        self.assertEqual(
            refresh_calls,
            [
                (
                    "QAT-1",
                    {"user": "unit.test@example.com", "mark_submitted": True, "student": "STU-1"},
                ),
                (
                    "QAT-2",
                    {"user": "unit.test@example.com", "mark_submitted": True, "student": "STU-2"},
                ),
            ],
        )
        self.assertEqual(payload, {"updated_item_count": 2, "updated_attempt_count": 2})

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

    def test_get_grid_returns_bounded_overview_payload_for_selected_group(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Delivery":
                    return [
                        {
                            "name": "TDL-0002",
                            "task": "TASK-2",
                            "grading_mode": "Points",
                            "rubric_scoring_strategy": None,
                            "due_date": "2026-04-04 10:00:00",
                            "delivery_mode": "Assess",
                            "allow_feedback": 0,
                            "max_points": 20,
                        },
                        {
                            "name": "TDL-0001",
                            "task": "TASK-1",
                            "grading_mode": "Criteria",
                            "rubric_scoring_strategy": "Separate Criteria",
                            "due_date": "2026-04-03 10:00:00",
                            "delivery_mode": "Assess",
                            "allow_feedback": 1,
                            "max_points": None,
                        },
                    ]
                if doctype == "Task":
                    return [
                        {"name": "TASK-1", "title": "Rubric reflection", "task_type": "Assignment"},
                        {"name": "TASK-2", "title": "Quiz score", "task_type": "Quiz"},
                    ]
                if doctype == "Task Outcome":
                    return [
                        {
                            "name": "OUT-1",
                            "task_delivery": "TDL-0001",
                            "student": "STU-1",
                            "grading_status": "Needs Review",
                            "procedural_status": None,
                            "has_submission": 1,
                            "has_new_submission": 1,
                            "official_score": None,
                            "official_grade": None,
                            "official_grade_value": None,
                            "official_feedback": "Great detail.",
                            "is_complete": 0,
                            "is_published": 0,
                        },
                        {
                            "name": "OUT-2",
                            "task_delivery": "TDL-0002",
                            "student": "STU-1",
                            "grading_status": "Released",
                            "procedural_status": None,
                            "has_submission": 1,
                            "has_new_submission": 0,
                            "official_score": 18,
                            "official_grade": "A",
                            "official_grade_value": "A",
                            "official_feedback": None,
                            "is_complete": 0,
                            "is_published": 1,
                        },
                    ]
                if doctype == "Task Outcome Criterion":
                    return [
                        {
                            "parent": "OUT-1",
                            "assessment_criteria": "CRIT-1",
                            "level": "Secure",
                            "level_points": 4,
                        }
                    ]
                return []

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.gradebook")
            module._can_read_gradebook = lambda: True
            module._resolve_gradebook_scope = lambda school, academic_year, course: {
                "courses": [course] if course else [],
                "student_groups": ["GRP-1"],
            }
            module._assert_group_access = lambda student_group: None
            module._get_student_display_map = lambda student_ids: {"STU-1": "Ada Lovelace"}
            module._get_student_meta_map = lambda student_ids: {"STU-1": {"student_id": "S-001", "student_image": None}}

            payload = module.get_grid(
                {
                    "school": "SCH-1",
                    "academic_year": "2025-2026",
                    "student_group": "GRP-1",
                    "limit": 2,
                }
            )

        self.assertEqual(
            payload["deliveries"],
            [
                {
                    "delivery_id": "TDL-0001",
                    "task_title": "Rubric reflection",
                    "grading_mode": "Criteria",
                    "rubric_scoring_strategy": "Separate Criteria",
                    "due_date": "2026-04-03 10:00:00",
                    "delivery_mode": "Assess",
                    "allow_feedback": 1,
                    "max_points": None,
                    "task_type": "Assignment",
                },
                {
                    "delivery_id": "TDL-0002",
                    "task_title": "Quiz score",
                    "grading_mode": "Points",
                    "rubric_scoring_strategy": None,
                    "due_date": "2026-04-04 10:00:00",
                    "delivery_mode": "Assess",
                    "allow_feedback": 0,
                    "max_points": 20.0,
                    "task_type": "Quiz",
                },
            ],
        )
        self.assertEqual(
            payload["students"],
            [
                {
                    "student": "STU-1",
                    "student_name": "Ada Lovelace",
                    "student_id": "S-001",
                    "student_image": None,
                }
            ],
        )
        self.assertEqual(
            payload["cells"][0]["official"]["criteria"], [{"criteria": "CRIT-1", "level": "Secure", "points": 4}]
        )
        self.assertTrue(payload["cells"][0]["flags"]["has_new_submission"])
        self.assertTrue(payload["cells"][1]["flags"]["is_published"])

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
