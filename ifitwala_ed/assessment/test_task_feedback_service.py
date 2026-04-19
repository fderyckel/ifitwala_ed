from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


class _FakeWorkspaceDoc:
    def __init__(self):
        self._is_new = True
        self.task_outcome = None
        self.task_submission = None
        self.submission_version = None
        self.feedback_visibility = None
        self.grade_visibility = None
        self.overall_summary = None
        self.strengths_summary = None
        self.improvements_summary = None
        self.next_steps_summary = None
        self.feedback_items = []
        self.inserted = False
        self.saved = False

    def is_new(self):
        return self._is_new

    def set(self, fieldname, value):
        setattr(self, fieldname, value)

    def append(self, fieldname, value):
        getattr(self, fieldname).append(value)

    def insert(self, ignore_permissions=False):
        self.inserted = ignore_permissions
        self._is_new = False

    def save(self, ignore_permissions=False):
        self.saved = ignore_permissions


class TestTaskFeedbackService(TestCase):
    def test_build_feedback_workspace_payload_derives_release_defaults_from_legacy_outcome(self):
        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Submission":
                    return {"name": "TSU-1", "task_outcome": "OUT-1", "version": 2}
                if doctype == "Task Outcome" and name_or_filters == "OUT-1":
                    return {
                        "name": "OUT-1",
                        "is_published": 1,
                        "published_on": "2026-04-19 10:00:00",
                        "published_by": "teacher@example.com",
                    }
                if doctype == "Task Feedback Workspace":
                    return None
                return None

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.assessment.task_feedback_service")
            payload = module.build_feedback_workspace_payload("OUT-1", "TSU-1")

        self.assertIsNone(payload["workspace_id"])
        self.assertEqual(payload["task_submission"], "TSU-1")
        self.assertEqual(payload["submission_version"], 2)
        self.assertEqual(payload["publication"]["feedback_visibility"], "student_and_guardian")
        self.assertEqual(payload["publication"]["grade_visibility"], "student_and_guardian")
        self.assertTrue(payload["publication"]["derived_from_legacy_outcome"])

    def test_save_feedback_workspace_draft_normalizes_structured_items(self):
        created_docs: list[_FakeWorkspaceDoc] = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Submission":
                    return {"name": "TSU-1", "task_outcome": "OUT-1", "version": 2}
                if doctype == "Task Feedback Workspace":
                    if isinstance(name_or_filters, dict):
                        if not created_docs or created_docs[0].is_new():
                            return None
                        return {
                            "name": "TFW-1",
                            "feedback_visibility": created_docs[0].feedback_visibility,
                            "grade_visibility": created_docs[0].grade_visibility,
                            "overall_summary": created_docs[0].overall_summary,
                            "strengths_summary": created_docs[0].strengths_summary,
                            "improvements_summary": created_docs[0].improvements_summary,
                            "next_steps_summary": created_docs[0].next_steps_summary,
                            "modified": None,
                            "modified_by": "unit.test@example.com",
                        }
                    return {
                        "name": "TFW-1",
                        "feedback_visibility": "hidden",
                        "grade_visibility": "hidden",
                        "overall_summary": "Prioritise the claim.",
                        "strengths_summary": "",
                        "improvements_summary": "",
                        "next_steps_summary": "",
                        "modified": None,
                        "modified_by": "unit.test@example.com",
                    }
                if doctype == "Task Outcome":
                    if fieldname == ["name", "is_published", "published_on", "published_by"]:
                        return {
                            "name": "OUT-1",
                            "is_published": 0,
                            "published_on": None,
                            "published_by": None,
                        }
                    return {
                        "task_delivery": "TDL-1",
                        "task": "TASK-1",
                        "student": "STU-1",
                        "student_group": "GRP-1",
                        "school": "SCH-1",
                        "course": "CRS-1",
                        "academic_year": "2025-2026",
                    }
                return None

            frappe.db.get_value = fake_get_value

            def fake_get_all(doctype, **kwargs):
                if doctype != "Task Feedback Item":
                    return []
                if not created_docs:
                    return []
                return [
                    {
                        "name": f"TFI-{index + 1}",
                        "anchor_kind": row["anchor_kind"],
                        "page_number": row["page_number"],
                        "feedback_intent": row["feedback_intent"],
                        "workflow_state": row["workflow_state"],
                        "body": row["body"],
                        "anchor_payload": row["anchor_payload"],
                        "assessment_criteria": row["assessment_criteria"],
                        "author": row["author"],
                    }
                    for index, row in enumerate(created_docs[0].feedback_items)
                ]

            frappe.get_all = fake_get_all
            frappe.new_doc = lambda doctype: created_docs.append(_FakeWorkspaceDoc()) or created_docs[-1]

            module = import_fresh("ifitwala_ed.assessment.task_feedback_service")
            payload = module.save_feedback_workspace_draft(
                {
                    "outcome_id": "OUT-1",
                    "submission_id": "TSU-1",
                    "summary": {"overall": "Prioritise the claim."},
                    "items": [
                        {
                            "kind": "rect",
                            "page": 2,
                            "intent": "issue",
                            "workflow_state": "draft",
                            "comment": "Tighten this paragraph.",
                            "anchor": {
                                "kind": "rect",
                                "page": 2,
                                "rect": {"x": 0.12, "y": 0.18, "width": 0.3, "height": 0.2},
                            },
                        }
                    ],
                }
            )

        self.assertTrue(created_docs[0].inserted)
        self.assertEqual(created_docs[0].submission_version, 2)
        self.assertEqual(len(created_docs[0].feedback_items), 1)
        self.assertEqual(created_docs[0].feedback_items[0]["anchor_kind"], "rect")
        self.assertEqual(payload["summary"]["overall"], "Prioritise the claim.")
        self.assertEqual(payload["items"][0]["kind"], "rect")
        self.assertEqual(payload["items"][0]["anchor"]["rect"]["width"], 0.3)

    def test_normalize_feedback_anchor_payload_rejects_invalid_coordinates(self):
        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.assessment.task_feedback_service")
            with self.assertRaises(StubValidationError):
                module.normalize_feedback_anchor_payload(
                    "point",
                    1,
                    {"point": {"x": 1.2, "y": 0.4}},
                )
