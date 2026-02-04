# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.assessment.task_contribution_service import (
	get_latest_submission_version,
	get_submission_version,
)
from ifitwala_ed.assessment.task_outcome_service import resolve_grade_symbol
from ifitwala_ed.assessment.task_outcome_service import apply_official_outcome_from_contributions


class TaskContribution(Document):
	def before_validate(self):
		self._ensure_contributor()
		self._ensure_submitted_on()
		self._require_links()
		outcome = self._get_outcome_context()
		self._stamp_context(outcome)
		self._ensure_submission_matches_outcome()
		self._ensure_latest_submission()

	def validate(self):
		self._validate_submission_requirement()
		self._validate_grade_value()
		self._validate_payload_for_grading_mode()

	def after_insert(self):
		if (self.status or "").strip() != "Draft":
			apply_official_outcome_from_contributions(self.task_outcome)

	def _doc_meta(self):
		if not hasattr(self, "_contrib_meta"):
			self._contrib_meta = frappe.get_meta(self.doctype)
		return self._contrib_meta

	def _has_field(self, fieldname):
		return bool(self._doc_meta().get_field(fieldname))

	def _require_links(self):
		if not self.task_outcome:
			frappe.throw(_("Task Outcome is required."))
		if not self.contributor:
			frappe.throw(_("Contributor is required."))
		status = (self.status or "Submitted").strip()
		if status != "Draft" and self._delivery_requires_submission() and not self.task_submission:
			frappe.throw(_("Task Submission is required."))

	def _get_outcome_context(self):
		if hasattr(self, "_outcome_row"):
			return self._outcome_row

		fields = [
			"task_delivery",
			"task",
			"student",
			"student_group",
			"course",
			"academic_year",
			"school",
			"grade_scale",
		]
		outcome = frappe.db.get_value(
			"Task Outcome",
			self.task_outcome,
			fields,
			as_dict=True,
		)
		if not outcome:
			frappe.throw(_("Task Outcome not found."))
		self._outcome_row = outcome
		return outcome

	def _stamp_context(self, outcome):
		for field in (
			"task_delivery",
			"task",
			"student",
			"student_group",
			"course",
			"academic_year",
			"school",
			"grade_scale",
		):
			if self._has_field(field) and outcome.get(field):
				setattr(self, field, outcome.get(field))

	def _ensure_submission_matches_outcome(self):
		if not self.task_submission:
			return
		submission_outcome = frappe.db.get_value(
			"Task Submission",
			self.task_submission,
			"task_outcome",
		)
		if not submission_outcome:
			frappe.throw(_("Task Submission not found."))
		if submission_outcome != self.task_outcome:
			frappe.throw(_("Submission does not belong to the selected outcome."))

	def _ensure_latest_submission(self):
		if not self.task_submission:
			return
		latest_version = get_latest_submission_version(self.task_outcome)
		submission_version = get_submission_version(self.task_submission)
		if submission_version < latest_version:
			frappe.throw(_("New submission exists; grade the latest version."))

	def _ensure_contributor(self):
		if not self.contributor:
			self.contributor = frappe.session.user

	def _ensure_submitted_on(self):
		if not self.submitted_on:
			self.submitted_on = now_datetime()

	def _validate_grade_value(self):
		grade_symbol = (self.grade or "").strip()
		if not grade_symbol:
			if self._has_field("grade_value"):
				self.grade_value = None
			return

		if not self.grade_scale:
			frappe.throw(_("Grade Scale is required to set a Grade."))

		grade_value = resolve_grade_symbol(self.grade_scale, grade_symbol)
		if self._has_field("grade_value"):
			if self.grade_value not in (None, ""):
				try:
					current = float(self.grade_value)
				except Exception:
					current = None
				if current is None or abs(current - grade_value) > 1e-9:
					frappe.throw(_("Grade Value is system-managed and must match the Grade Scale."))
			self.grade_value = grade_value

	def _validate_payload_for_grading_mode(self):
		delivery = self._get_delivery_flags()
		grading_mode = (delivery.get("grading_mode") or "").strip()
		requires_grading = int(delivery.get("require_grading") or 0)

		if not requires_grading:
			if self.score not in (None, "") or (self.grade or "").strip():
				frappe.throw(_("Ungraded deliveries only allow feedback contributions."))
			if self.get("rubric_scores"):
				frappe.throw(_("Ungraded deliveries only allow feedback contributions."))
			return

		if grading_mode == "Points" and self.score in (None, ""):
			frappe.throw(_("Score is required for points grading."))

		if grading_mode == "Criteria":
			rows = self.get("rubric_scores") or []
			if not rows:
				frappe.throw(_("Rubric scores are required for criteria grading."))

	def _validate_submission_requirement(self):
		status = (self.status or "Submitted").strip()
		if status == "Draft":
			return
		if self._delivery_requires_submission() and not self.task_submission:
			frappe.throw(_("Task Submission is required."))

	def _get_delivery_flags(self):
		outcome = self._get_outcome_context()
		if not outcome.get("task_delivery"):
			return {}

		fields = ["grading_mode", "require_grading", "delivery_mode", "requires_submission"]
		return frappe.db.get_value(
			"Task Delivery",
			outcome["task_delivery"],
			fields,
			as_dict=True,
		) or {}

	def _delivery_requires_submission(self):
		delivery = self._get_delivery_flags()
		return int(delivery.get("requires_submission") or 0) == 1


def on_doctype_update():
	_ensure_indexes()


def _ensure_indexes():
	table = "tabTask Contribution"
	idx_outcome = "idx_task_contribution_outcome_stale_modified"
	idx_submission = "idx_task_contribution_submission"
	idx_contributor = "idx_task_contribution_contributor_modified"

	rows = frappe.db.sql(
		"SHOW INDEX FROM `{}`".format(table),
		as_dict=True,
	)

	if not _index_exists(rows, idx_outcome):
		frappe.db.sql(
			f"ALTER TABLE `{table}` ADD INDEX `{idx_outcome}` (`task_outcome`, `is_stale`, `modified`)"
		)

	rows = frappe.db.sql(
		"SHOW INDEX FROM `{}`".format(table),
		as_dict=True,
	)
	if not _index_exists(rows, idx_submission):
		frappe.db.sql(
			f"ALTER TABLE `{table}` ADD INDEX `{idx_submission}` (`task_submission`)"
		)

	rows = frappe.db.sql(
		"SHOW INDEX FROM `{}`".format(table),
		as_dict=True,
	)
	if not _index_exists(rows, idx_contributor):
		frappe.db.sql(
			f"ALTER TABLE `{table}` ADD INDEX `{idx_contributor}` (`contributor`, `modified`)"
		)


def _index_exists(rows, index_name):
	return any(row.get("Key_name") == index_name for row in rows)
