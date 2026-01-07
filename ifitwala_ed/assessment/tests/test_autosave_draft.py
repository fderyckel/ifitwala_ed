# Copyright (c) 2026, Francois de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.assessment import task_contribution_service


class TestAutosaveDraft(FrappeTestCase):
	def test_draft_autosave_does_not_create_submission(self):
		row = self._find_outcome_without_submissions()
		if not row:
			self.skipTest("No eligible Task Outcome without submissions found.")

		outcome_id = row["outcome"]
		draft_payload = self._draft_payload(row)

		before_counts = self._submission_counts(outcome_id)
		before_flags = self._outcome_flags(outcome_id)

		draft_result = task_contribution_service.save_draft_contribution(
			draft_payload,
			contributor=frappe.session.user,
		)

		after_counts = self._submission_counts(outcome_id)
		after_flags = self._outcome_flags(outcome_id)

		self.assertEqual(draft_result.get("status"), "Draft")
		self.assertEqual(after_counts, before_counts)
		self.assertEqual(after_flags, before_flags)

		draft_contribution = draft_result.get("contribution")
		submit_result = None
		try:
			submit_result = task_contribution_service.submit_contribution(
				self._draft_payload(row),
				contributor=frappe.session.user,
			)
			self.assertEqual(submit_result.get("status"), "Submitted")
			self.assertEqual(
				self._submission_counts(outcome_id),
				before_counts + 1,
			)
			submission_id = submit_result.get("task_submission")
			self.assertTrue(submission_id)
			is_stub = frappe.db.get_value("Task Submission", submission_id, "is_stub")
			self.assertEqual(int(is_stub or 0), 1)
			self.assertTrue(submit_result.get("outcome_update"))
		finally:
			if submit_result and submit_result.get("contribution"):
				frappe.delete_doc(
					"Task Contribution",
					submit_result.get("contribution"),
					ignore_permissions=True,
					force=1,
				)
			if submit_result and submit_result.get("task_submission"):
				frappe.delete_doc(
					"Task Submission",
					submit_result.get("task_submission"),
					ignore_permissions=True,
					force=1,
				)
			if draft_contribution:
				frappe.delete_doc(
					"Task Contribution",
					draft_contribution,
					ignore_permissions=True,
					force=1,
				)

	def _find_outcome_without_submissions(self):
		rows = frappe.db.sql(
			"""
			SELECT
				o.name AS outcome,
				d.grading_mode,
				d.require_grading,
				d.delivery_mode
			FROM `tabTask Outcome` o
			JOIN `tabTask Delivery` d ON d.name = o.task_delivery
			LEFT JOIN `tabTask Submission` s ON s.task_outcome = o.name
			WHERE s.name IS NULL
			  AND d.delivery_mode = 'Assess'
			  AND (d.grading_mode IS NULL OR d.grading_mode != 'Criteria')
			LIMIT 1
			""",
			as_dict=True,
		)
		return rows[0] if rows else None

	def _draft_payload(self, row):
		payload = {
			"task_outcome": row.get("outcome"),
			"contribution_type": "Self",
		}
		if row.get("grading_mode") == "Points" and int(row.get("require_grading") or 0) == 1:
			payload["score"] = 1
		return payload

	def _submission_counts(self, outcome_id):
		return frappe.db.count("Task Submission", {"task_outcome": outcome_id})

	def _outcome_flags(self, outcome_id):
		row = frappe.db.get_value(
			"Task Outcome",
			outcome_id,
			["has_submission", "has_new_submission"],
			as_dict=True,
		) or {}
		return {
			"has_submission": int(row.get("has_submission") or 0),
			"has_new_submission": int(row.get("has_new_submission") or 0),
		}
