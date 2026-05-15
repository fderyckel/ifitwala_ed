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

    def test_build_released_result_payload_masks_grade_when_only_feedback_is_released(self):
        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    return {
                        "name": "OUT-1",
                        "official_score": 18,
                        "official_grade": "A",
                        "official_grade_value": 4,
                        "official_feedback": "Tighten the conclusion.",
                        "is_published": 0,
                        "published_on": None,
                        "published_by": None,
                    }
                if doctype == "Task Submission":
                    return {"name": "TSU-1", "task_outcome": "OUT-1", "version": 2}
                if doctype == "Task Feedback Workspace":
                    return {
                        "name": "TFW-1",
                        "feedback_visibility": "student",
                        "grade_visibility": "hidden",
                        "overall_summary": "Strong reasoning overall.",
                        "strengths_summary": "",
                        "improvements_summary": "Clarify the final paragraph.",
                        "next_steps_summary": "",
                        "modified": "2026-04-20 10:00:00",
                        "modified_by": "teacher@example.com",
                    }
                return None

            frappe.db.get_value = fake_get_value
            frappe.get_all = lambda doctype, **kwargs: []

            module = import_fresh("ifitwala_ed.assessment.task_feedback_service")
            payload = module.build_released_result_payload(
                "OUT-1",
                audience="student",
                submission_id="TSU-1",
            )

        self.assertFalse(payload["grade_visible"])
        self.assertTrue(payload["feedback_visible"])
        self.assertIsNone(payload["official"]["score"])
        self.assertEqual(payload["feedback"]["summary"]["overall"], "Strong reasoning overall.")
        self.assertEqual(payload["feedback"]["summary"]["improvements"], "Clarify the final paragraph.")

    def test_build_released_result_payload_uses_legacy_publish_defaults_without_workspace(self):
        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    return {
                        "name": "OUT-2",
                        "official_score": 12,
                        "official_grade": "B",
                        "official_grade_value": 3,
                        "official_feedback": "Keep supporting each claim.",
                        "is_published": 1,
                        "published_on": "2026-04-20 12:00:00",
                        "published_by": "teacher@example.com",
                    }
                return None

            frappe.db.get_value = fake_get_value
            frappe.get_all = lambda doctype, **kwargs: []

            module = import_fresh("ifitwala_ed.assessment.task_feedback_service")
            payload = module.build_released_result_payload("OUT-2", audience="student")

        self.assertTrue(payload["grade_visible"])
        self.assertTrue(payload["feedback_visible"])
        self.assertEqual(payload["official"]["score"], 12)
        self.assertEqual(payload["official"]["feedback"], "Keep supporting each claim.")
        self.assertEqual(payload["feedback"]["summary"]["overall"], "Keep supporting each claim.")

    def test_released_feedback_detail_returns_empty_priorities_when_none_exist(self):
        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    return {
                        "name": "OUT-1",
                        "task_delivery": "TDL-1",
                        "task": "TASK-1",
                        "student": "STU-1",
                        "course": "CRS-1",
                        "official_score": None,
                        "official_grade": None,
                        "official_grade_value": None,
                        "official_feedback": "Legacy fallback",
                        "is_published": 0,
                        "published_on": None,
                        "published_by": None,
                    }
                if doctype == "Task Submission":
                    return {"name": "TSU-1", "task_outcome": "OUT-1", "version": 2}
                if doctype == "Task Feedback Workspace":
                    return {
                        "name": "TFW-1",
                        "feedback_visibility": "student_and_guardian",
                        "grade_visibility": "hidden",
                        "overall_summary": "Released summary",
                        "strengths_summary": "",
                        "improvements_summary": "",
                        "next_steps_summary": "",
                        "modified": "2026-04-23 10:00:00",
                        "modified_by": "teacher@example.com",
                    }
                if doctype == "Task Delivery":
                    return {"name": "TDL-1", "title": "Source Analysis", "task_type": "assignment"}
                if doctype == "Course" and fieldname == "course_name":
                    return "History"
                return None

            def fake_get_all(doctype, **kwargs):
                if doctype == "Task Feedback Item":
                    return [
                        {
                            "name": "TFI-1",
                            "anchor_kind": "page",
                            "page_number": 1,
                            "feedback_intent": "issue",
                            "workflow_state": "published",
                            "body": "Clarify the evidence.",
                            "anchor_payload": '{"kind":"page","page":1}',
                            "assessment_criteria": None,
                            "author": "teacher@example.com",
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.assessment.task_feedback_service")
            payload = module.build_released_feedback_detail_payload(
                "OUT-1",
                audience="guardian",
                submission_id="TSU-1",
            )

        self.assertTrue(payload["feedback_visible"])
        self.assertEqual(payload["feedback"]["summary"]["overall"], "Released summary")
        self.assertEqual(len(payload["feedback"]["items"]), 1)
        self.assertEqual(payload["feedback"]["priorities"], [])

    def test_released_feedback_detail_falls_back_to_legacy_when_feedback_workspace_is_missing(self):
        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    return {
                        "name": "OUT-2",
                        "task_delivery": "TDL-2",
                        "task": "TASK-2",
                        "student": "STU-2",
                        "course": "CRS-2",
                        "official_score": 14,
                        "official_grade": "B",
                        "official_grade_value": 3,
                        "official_feedback": "Keep supporting each claim.",
                        "is_published": 1,
                        "published_on": "2026-04-20 12:00:00",
                        "published_by": "teacher@example.com",
                    }
                if doctype == "Task Submission":
                    return {"name": "TSU-2", "task_outcome": "OUT-2", "version": 3}
                if doctype == "Task Delivery":
                    return {"name": "TDL-2", "title": "Essay", "task_type": "assignment"}
                if doctype == "Course" and fieldname == "course_name":
                    return "English"
                return None

            frappe.db.get_value = fake_get_value
            frappe.get_all = lambda doctype, **kwargs: []

            module = import_fresh("ifitwala_ed.assessment.task_feedback_service")
            payload = module.build_released_feedback_detail_payload(
                "OUT-2",
                audience="guardian",
                submission_id="TSU-2",
            )

        self.assertTrue(payload["grade_visible"])
        self.assertTrue(payload["feedback_visible"])
        self.assertEqual(payload["official"]["score"], 14)
        self.assertEqual(payload["feedback"]["summary"]["overall"], "Keep supporting each claim.")
        self.assertEqual(payload["feedback"]["items"], [])
        self.assertEqual(payload["feedback"]["priorities"], [])

    def test_build_publication_state_map_prefers_latest_workspace_over_legacy_flag(self):
        with stubbed_frappe() as frappe:

            def fake_get_all(doctype, **kwargs):
                if doctype == "Task Outcome":
                    return [
                        {
                            "name": "OUT-1",
                            "is_published": 1,
                            "published_on": "2026-04-20 12:00:00",
                            "published_by": "teacher@example.com",
                        }
                    ]
                if doctype == "Task Submission":
                    return [
                        {
                            "name": "TSU-2",
                            "task_outcome": "OUT-1",
                            "version": 2,
                            "modified": "2026-04-22 09:00:00",
                        },
                        {
                            "name": "TSU-1",
                            "task_outcome": "OUT-1",
                            "version": 1,
                            "modified": "2026-04-21 09:00:00",
                        },
                    ]
                if doctype == "Task Feedback Workspace":
                    return [
                        {
                            "name": "TFW-2",
                            "task_outcome": "OUT-1",
                            "task_submission": "TSU-2",
                            "feedback_visibility": "student",
                            "grade_visibility": "hidden",
                            "modified": "2026-04-22 10:00:00",
                        }
                    ]
                return []

            frappe.get_all = fake_get_all
            module = import_fresh("ifitwala_ed.assessment.task_feedback_service")
            payload = module.build_publication_state_map(["OUT-1"])

        state = payload["OUT-1"]
        self.assertFalse(state["derived_from_legacy_outcome"])
        self.assertTrue(state["legacy_outcome_published"])
        self.assertTrue(state["visible_to_student"])
        self.assertFalse(state["visible_to_guardian"])
        self.assertTrue(state["is_visible_to_any_audience"])
