from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeWorkspaceDoc:
    def __init__(self, name="TFW-1"):
        self.name = name


class _FakeThreadDoc:
    def __init__(self):
        self.name = "TFT-1"
        self._is_new = True
        self.task_feedback_workspace = None
        self.target_type = None
        self.target_feedback_item = None
        self.target_priority = None
        self.summary_field = None
        self.learner_state = "none"
        self.thread_status = "open"
        self.messages = []

    def is_new(self):
        return self._is_new

    def append(self, fieldname, value):
        getattr(self, fieldname).append(value)

    def get(self, fieldname):
        return getattr(self, fieldname)

    def insert(self, ignore_permissions=False):
        self._is_new = False

    def save(self, ignore_permissions=False):
        self._is_new = False


class TestTaskFeedbackThreadService(TestCase):
    def test_build_feedback_thread_payloads_includes_messages_for_workspace(self):
        with stubbed_frappe() as frappe:

            def fake_get_all(doctype, **kwargs):
                if doctype == "Task Feedback Thread":
                    return [
                        {
                            "name": "TFT-1",
                            "target_type": "feedback_item",
                            "target_feedback_item": "TFI-1",
                            "target_priority": None,
                            "summary_field": None,
                            "learner_state": "understood",
                            "thread_status": "open",
                            "modified": "2026-04-22 14:30:00",
                            "modified_by": "teacher@example.com",
                        }
                    ]
                if doctype == "Task Feedback Thread Message":
                    return [
                        {
                            "name": "MSG-1",
                            "parent": "TFT-1",
                            "author": "student@example.com",
                            "author_role": "student",
                            "message_kind": "clarification",
                            "body": "Can you explain this note?",
                            "creation": "2026-04-22 14:00:00",
                        }
                    ]
                return []

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.assessment.task_feedback_thread_service")
            payload = module.build_feedback_thread_payloads(workspace_id="TFW-1")

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["target_feedback_item"], "TFI-1")
        self.assertEqual(payload[0]["messages"][0]["message_kind"], "clarification")
        self.assertEqual(payload[0]["learner_state"], "understood")

    def test_save_student_reply_creates_thread_against_workspace_and_returns_payload(self):
        created_docs: list[_FakeThreadDoc] = []
        saved_doc = _FakeThreadDoc()

        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Feedback Workspace":
                    if isinstance(name_or_filters, dict):
                        return "TFW-1"
                if doctype == "Task Feedback Thread":
                    if isinstance(name_or_filters, dict):
                        return None
                    if name_or_filters == "TFT-1" and fieldname == "task_feedback_workspace":
                        return "TFW-1"
                return None

            def fake_get_all(doctype, **kwargs):
                if doctype == "Task Feedback Thread":
                    if not created_docs:
                        return []
                    return [
                        {
                            "name": saved_doc.name,
                            "target_type": saved_doc.target_type,
                            "target_feedback_item": saved_doc.target_feedback_item,
                            "target_priority": saved_doc.target_priority,
                            "summary_field": saved_doc.summary_field,
                            "learner_state": saved_doc.learner_state,
                            "thread_status": saved_doc.thread_status,
                            "modified": "2026-04-22 15:00:00",
                            "modified_by": "unit.test@example.com",
                        }
                    ]
                if doctype == "Task Feedback Thread Message":
                    if not created_docs:
                        return []
                    return [
                        {
                            "name": "MSG-1",
                            "parent": saved_doc.name,
                            "author": "unit.test@example.com",
                            "author_role": "student",
                            "message_kind": "clarification",
                            "body": "Please explain this comment.",
                            "creation": "2026-04-22 15:00:00",
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all
            frappe.get_doc = lambda doctype, name: (
                _FakeWorkspaceDoc(name) if doctype == "Task Feedback Workspace" else None
            )
            frappe.new_doc = lambda doctype: created_docs.append(saved_doc) or saved_doc

            module = import_fresh("ifitwala_ed.assessment.task_feedback_thread_service")
            payload = module.save_student_reply(
                {
                    "outcome_id": "OUT-1",
                    "submission_id": "TSU-1",
                    "target_type": "feedback_item",
                    "target_feedback_item": "TFI-1",
                    "message_kind": "clarification",
                    "body": "Please explain this comment.",
                }
            )

        self.assertEqual(len(created_docs), 1)
        self.assertEqual(saved_doc.task_feedback_workspace, "TFW-1")
        self.assertEqual(saved_doc.target_feedback_item, "TFI-1")
        self.assertEqual(saved_doc.messages[0]["message_kind"], "clarification")
        self.assertEqual(payload["thread_id"], "TFT-1")
        self.assertEqual(payload["messages"][0]["body"], "Please explain this comment.")
