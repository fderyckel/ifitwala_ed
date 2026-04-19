# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


def _import_task_submission_module():
    task_submission_service = types.ModuleType("ifitwala_ed.assessment.task_submission_service")
    task_submission_service.apply_outcome_submission_effects = lambda *args, **kwargs: None
    task_submission_service.get_next_submission_version = lambda outcome_id: 1
    task_submission_service.stamp_submission_context = lambda doc, outcome: None

    with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_submission_service": task_submission_service}):
        return import_fresh("ifitwala_ed.assessment.doctype.task_submission.task_submission")


class TestTaskSubmission(TestCase):
    def test_attachments_changed_detects_no_change(self):
        module = _import_task_submission_module()
        before = [{"file": "/files/a.pdf", "external_url": "", "description": "A"}]
        after = [{"file": "/files/a.pdf", "external_url": "", "description": "A"}]

        self.assertFalse(module._attachments_changed(before, after))

    def test_attachments_changed_detects_modified_payload(self):
        module = _import_task_submission_module()
        before = [{"file": "/files/a.pdf", "external_url": "", "description": "A"}]
        after = [{"file": "/files/a.pdf", "external_url": "", "description": "Updated"}]

        self.assertTrue(module._attachments_changed(before, after))

    def test_unique_index_exists_requires_unique_constraint(self):
        module = _import_task_submission_module()
        rows = [
            {
                "Key_name": "uniq_task_submission_outcome_version",
                "Non_unique": 0,
                "Seq_in_index": 1,
                "Column_name": "task_outcome",
            },
            {
                "Key_name": "uniq_task_submission_outcome_version",
                "Non_unique": 0,
                "Seq_in_index": 2,
                "Column_name": "version",
            },
        ]

        self.assertTrue(module._unique_index_exists(rows, ["task_outcome", "version"]))

    def test_validate_evidence_presence_allows_stub_without_file_link_or_text(self):
        module = _import_task_submission_module()
        submission = module.TaskSubmission()
        submission.is_stub = 1
        submission.link_url = None
        submission.text_content = None
        submission.get = lambda fieldname: [] if fieldname == "attachments" else None

        submission._validate_evidence_presence()

    def test_validate_evidence_presence_rejects_non_stub_without_file_link_or_text(self):
        module = _import_task_submission_module()
        submission = module.TaskSubmission()
        submission.is_stub = 0
        submission.link_url = None
        submission.text_content = None
        submission.get = lambda fieldname: [] if fieldname == "attachments" else None

        with self.assertRaises(StubValidationError):
            submission._validate_evidence_presence()
