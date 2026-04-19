from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubPermissionError, StubValidationError, import_fresh, stubbed_frappe


class _FakeCommentBankDoc:
    def __init__(self, *, owner="unit.test@example.com", is_new=True):
        self.owner = owner
        self._is_new = is_new
        self.entry_label = None
        self.body = None
        self.feedback_intent = None
        self.scope_mode = None
        self.assessment_criteria = None
        self.course = None
        self.task = None
        self.is_active = 1
        self.inserted = False
        self.saved = False

    def is_new(self):
        return self._is_new

    def insert(self, ignore_permissions=False):
        self.inserted = ignore_permissions
        self._is_new = False

    def save(self, ignore_permissions=False):
        self.saved = ignore_permissions


class TestTaskFeedbackCommentBankService(TestCase):
    def test_build_comment_bank_payload_filters_and_prioritizes_relevant_entries(self):
        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and name_or_filters == "OUT-1":
                    return {
                        "name": "OUT-1",
                        "task_delivery": "TDL-1",
                        "task": "TASK-1",
                        "course": "CRS-1",
                    }
                if doctype == "Task" and name_or_filters == "TASK-1":
                    return {
                        "name": "TASK-1",
                        "title": "Source Analysis",
                        "default_course": "CRS-1",
                    }
                if doctype == "Task Delivery" and name_or_filters == "TDL-1":
                    return {
                        "name": "TDL-1",
                        "grading_mode": "Criteria",
                        "rubric_version": "TRV-1",
                    }
                return None

            def fake_get_all(doctype, **kwargs):
                if doctype == "Task Rubric Criterion":
                    return [
                        {
                            "assessment_criteria": "CRIT-THESIS",
                            "criteria_name": "Thesis",
                        }
                    ]
                if doctype == "Task Feedback Comment Bank Entry":
                    return [
                        {
                            "name": "BANK-COURSE",
                            "entry_label": "Course note",
                            "body": "Clarify the thesis earlier.",
                            "feedback_intent": "next_step",
                            "scope_mode": "course",
                            "course": "CRS-1",
                            "task": "",
                            "assessment_criteria": "CRIT-THESIS",
                            "modified": "2026-04-19 14:00:00",
                        },
                        {
                            "name": "BANK-TASK",
                            "entry_label": "Task note",
                            "body": "Support the claim with evidence.",
                            "feedback_intent": "issue",
                            "scope_mode": "task",
                            "course": "CRS-1",
                            "task": "TASK-1",
                            "assessment_criteria": "",
                            "modified": "2026-04-19 13:00:00",
                        },
                        {
                            "name": "BANK-OTHER",
                            "entry_label": "Other course",
                            "body": "This should not appear.",
                            "feedback_intent": "issue",
                            "scope_mode": "course",
                            "course": "CRS-2",
                            "task": "",
                            "assessment_criteria": "",
                            "modified": "2026-04-19 12:00:00",
                        },
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.assessment.task_feedback_comment_bank_service")
            payload = module.build_comment_bank_payload("OUT-1")

        self.assertEqual(payload["context"]["task"], "TASK-1")
        self.assertEqual(len(payload["entries"]), 2)
        self.assertEqual(payload["entries"][0]["id"], "BANK-COURSE")
        self.assertEqual(payload["entries"][0]["match_reasons"], ["course", "criterion"])
        self.assertEqual(payload["entries"][1]["id"], "BANK-TASK")
        self.assertEqual(payload["entries"][1]["match_reasons"], ["task"])

    def test_save_comment_bank_entry_stamps_task_scope_from_outcome(self):
        created_docs: list[_FakeCommentBankDoc] = []

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and name_or_filters == "OUT-1":
                    return {
                        "name": "OUT-1",
                        "task_delivery": "TDL-1",
                        "task": "TASK-1",
                        "course": "CRS-1",
                    }
                if doctype == "Task" and name_or_filters == "TASK-1":
                    return {
                        "name": "TASK-1",
                        "title": "Source Analysis",
                        "default_course": "CRS-1",
                    }
                if doctype == "Task Delivery" and name_or_filters == "TDL-1":
                    return {
                        "name": "TDL-1",
                        "grading_mode": "Criteria",
                        "rubric_version": "TRV-1",
                    }
                return None

            def fake_get_all(doctype, **kwargs):
                if doctype == "Task Rubric Criterion":
                    return [
                        {
                            "assessment_criteria": "CRIT-THESIS",
                            "criteria_name": "Thesis",
                        }
                    ]
                if doctype == "Task Feedback Comment Bank Entry":
                    if not created_docs:
                        return []
                    return [
                        {
                            "name": "BANK-NEW",
                            "entry_label": created_docs[0].entry_label,
                            "body": created_docs[0].body,
                            "feedback_intent": created_docs[0].feedback_intent,
                            "scope_mode": created_docs[0].scope_mode,
                            "course": created_docs[0].course,
                            "task": created_docs[0].task,
                            "assessment_criteria": created_docs[0].assessment_criteria,
                            "modified": "2026-04-19 14:00:00",
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all
            frappe.new_doc = lambda doctype: created_docs.append(_FakeCommentBankDoc()) or created_docs[-1]

            module = import_fresh("ifitwala_ed.assessment.task_feedback_comment_bank_service")
            payload = module.save_comment_bank_entry(
                {
                    "outcome_id": "OUT-1",
                    "body": "Support the thesis with direct evidence from the source.",
                    "feedback_intent": "next_step",
                    "assessment_criteria": "CRIT-THESIS",
                    "scope_mode": "task",
                }
            )

        self.assertTrue(created_docs[0].inserted)
        self.assertEqual(created_docs[0].course, "CRS-1")
        self.assertEqual(created_docs[0].task, "TASK-1")
        self.assertEqual(created_docs[0].scope_mode, "task")
        self.assertEqual(payload["entries"][0]["scope_mode"], "task")
        self.assertEqual(payload["entries"][0]["assessment_criteria"], "CRIT-THESIS")

    def test_save_comment_bank_entry_rejects_updates_to_other_users_entry(self):
        with stubbed_frappe() as frappe:
            frappe.db.get_value = lambda *args, **kwargs: {
                "name": "OUT-1",
                "task_delivery": "TDL-1",
                "task": "TASK-1",
                "course": "CRS-1",
            }
            frappe.get_all = lambda *args, **kwargs: []
            frappe.get_doc = lambda doctype, name: _FakeCommentBankDoc(owner="other@example.com", is_new=False)

            module = import_fresh("ifitwala_ed.assessment.task_feedback_comment_bank_service")
            with self.assertRaises(StubPermissionError):
                module.save_comment_bank_entry(
                    {
                        "outcome_id": "OUT-1",
                        "entry_id": "BANK-1",
                        "body": "Updated",
                        "feedback_intent": "issue",
                    }
                )

    def test_save_comment_bank_entry_rejects_unknown_scope(self):
        with stubbed_frappe() as frappe:
            frappe.db.get_value = lambda *args, **kwargs: {
                "name": "OUT-1",
                "task_delivery": "TDL-1",
                "task": "TASK-1",
                "course": "CRS-1",
            }
            frappe.get_all = lambda *args, **kwargs: []

            module = import_fresh("ifitwala_ed.assessment.task_feedback_comment_bank_service")
            with self.assertRaises(StubValidationError):
                module.save_comment_bank_entry(
                    {
                        "outcome_id": "OUT-1",
                        "body": "Updated",
                        "feedback_intent": "issue",
                        "scope_mode": "school",
                    }
                )
