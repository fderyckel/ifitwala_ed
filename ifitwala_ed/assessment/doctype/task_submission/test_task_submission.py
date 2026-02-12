# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py

from unittest import TestCase

from ifitwala_ed.assessment.doctype.task_submission.task_submission import (
	_attachments_changed,
	_unique_index_exists,
)


class TestTaskSubmission(TestCase):
	def test_attachments_changed_detects_no_change(self):
		before = [{"file": "/files/a.pdf", "external_url": "", "description": "A"}]
		after = [{"file": "/files/a.pdf", "external_url": "", "description": "A"}]

		self.assertFalse(_attachments_changed(before, after))

	def test_attachments_changed_detects_modified_payload(self):
		before = [{"file": "/files/a.pdf", "external_url": "", "description": "A"}]
		after = [{"file": "/files/a.pdf", "external_url": "", "description": "Updated"}]

		self.assertTrue(_attachments_changed(before, after))

	def test_unique_index_exists_requires_unique_constraint(self):
		rows = [
			{"Key_name": "uniq_task_submission_outcome_version", "Non_unique": 0, "Seq_in_index": 1, "Column_name": "task_outcome"},
			{"Key_name": "uniq_task_submission_outcome_version", "Non_unique": 0, "Seq_in_index": 2, "Column_name": "version"},
		]

		self.assertTrue(_unique_index_exists(rows, ["task_outcome", "version"]))
