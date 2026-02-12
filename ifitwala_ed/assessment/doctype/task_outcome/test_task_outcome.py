# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py

from unittest import TestCase

from ifitwala_ed.assessment.doctype.task_outcome.task_outcome import _unique_index_exists


class TestTaskOutcome(TestCase):
	def test_unique_index_exists_matches_ordered_columns(self):
		rows = [
			{"Key_name": "uniq_task_outcome_delivery_student", "Non_unique": 0, "Seq_in_index": 1, "Column_name": "task_delivery"},
			{"Key_name": "uniq_task_outcome_delivery_student", "Non_unique": 0, "Seq_in_index": 2, "Column_name": "student"},
		]

		self.assertTrue(_unique_index_exists(rows, ["task_delivery", "student"]))

	def test_unique_index_exists_ignores_non_unique_index(self):
		rows = [
			{"Key_name": "idx_task_outcome_delivery_student", "Non_unique": 1, "Seq_in_index": 1, "Column_name": "task_delivery"},
			{"Key_name": "idx_task_outcome_delivery_student", "Non_unique": 1, "Seq_in_index": 2, "Column_name": "student"},
		]

		self.assertFalse(_unique_index_exists(rows, ["task_delivery", "student"]))
