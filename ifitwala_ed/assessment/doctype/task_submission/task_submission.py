# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

from ifitwala_ed.assessment.task_submission_service import (
	apply_outcome_submission_effects,
	clone_group_submission,
	get_next_submission_version,
	stamp_submission_context,
)


class TaskSubmission(Document):
	def before_validate(self):
		self._require_outcome()
		outcome = self._get_outcome_context()
		stamp_submission_context(self, outcome)
		self._ensure_submission_metadata()
		self._set_version(outcome)

	def validate(self):
		self._validate_delivery_lock()
		self._validate_evidence_presence()
		self._prevent_evidence_overwrite()

	def after_insert(self):
		apply_outcome_submission_effects(self.task_outcome, self.name)
		self._maybe_clone_group_submission()

	def _doc_meta(self):
		if not hasattr(self, "_submission_meta"):
			self._submission_meta = frappe.get_meta(self.doctype)
		return self._submission_meta

	def _has_field(self, fieldname):
		return bool(self._doc_meta().get_field(fieldname))

	def _require_outcome(self):
		if not self.task_outcome:
			frappe.throw(_("Task Outcome is required."))

	def _get_outcome_context(self):
		if hasattr(self, "_outcome_row"):
			return self._outcome_row

		fields = [
			"student",
			"student_group",
			"course",
			"academic_year",
			"school",
			"task_delivery",
			"task",
			"procedural_status",
			"grading_status",
		]
		row = frappe.db.get_value(
			"Task Outcome",
			self.task_outcome,
			fields,
			as_dict=True,
		)
		if not row:
			frappe.throw(_("Task Outcome not found."))
		self._outcome_row = row
		return row

	def _ensure_submission_metadata(self):
		if not self.submitted_by:
			self.submitted_by = frappe.session.user
		if not self.submitted_on:
			self.submitted_on = now_datetime()

	def _set_version(self, outcome):
		self.version = get_next_submission_version(self.task_outcome)

	def _get_delivery(self):
		if hasattr(self, "_delivery_row"):
			return self._delivery_row

		outcome = self._get_outcome_context()
		task_delivery = outcome.get("task_delivery")
		if not task_delivery:
			self._delivery_row = {}
			return self._delivery_row

		fields = ["lock_date", "due_date", "allow_late_submission", "group_submission"]
		delivery = frappe.db.get_value(
			"Task Delivery",
			task_delivery,
			fields,
			as_dict=True,
		) or {}
		self._delivery_row = delivery
		return delivery

	def _validate_delivery_lock(self):
		delivery = self._get_delivery()
		if not delivery:
			return

		now = now_datetime()
		lock_date = get_datetime(delivery.get("lock_date")) if delivery.get("lock_date") else None
		if lock_date and now > lock_date:
			extension = self._get_outcome_context().get("procedural_status") == "Extension Granted"
			if not delivery.get("allow_late_submission") and not extension:
				frappe.throw(_("Submissions are locked for this delivery."))

		due_date = get_datetime(delivery.get("due_date")) if delivery.get("due_date") else None
		extension = self._get_outcome_context().get("procedural_status") == "Extension Granted"
		self.is_late = 1 if (due_date and now > due_date and not extension) else 0

	def _validate_evidence_presence(self):
		has_attachments = bool(self.get("attachments"))
		has_link = bool((self.link_url or "").strip())
		has_text = bool((self.text_content or "").strip())

		if not (has_attachments or has_link or has_text):
			frappe.throw(_("Provide a file, link, or text submission."))

	def _prevent_evidence_overwrite(self):
		if self.is_new():
			return

		before = self.get_doc_before_save()
		if not before:
			return

		if (before.link_url or "") != (self.link_url or ""):
			frappe.throw(_("Submissions are append-only. Create a new version instead of editing evidence."))

		if (before.text_content or "") != (self.text_content or ""):
			frappe.throw(_("Submissions are append-only. Create a new version instead of editing evidence."))

		if _attachments_changed(before.get("attachments"), self.get("attachments")):
			frappe.throw(_("Submissions are append-only. Create a new version instead of editing evidence."))

	def _maybe_clone_group_submission(self):
		delivery = self._get_delivery()
		if not delivery.get("group_submission"):
			return

		group_outcomes = self.flags.get("group_member_outcomes") or []
		if not group_outcomes:
			return

		rows = frappe.db.get_values(
			"Task Outcome",
			{
				"name": ["in", group_outcomes],
				"task_delivery": self.task_delivery,
			},
			"name",
			as_list=True,
		)
		filtered = [row[0] for row in rows if row and row[0]]
		if not filtered:
			return

		clone_group_submission(self.name, filtered)


def _attachments_changed(before_rows, after_rows):
	def _signature(rows):
		if not rows:
			return []
		return sorted(
			[
				(
					(row.get("file") or ""),
					(row.get("external_url") or ""),
					(row.get("description") or ""),
				)
				for row in rows
			]
		)

	return _signature(before_rows) != _signature(after_rows)


def on_doctype_update():
	_ensure_indexes()


def _ensure_indexes():
	table = "tabTask Submission"
	unique_name = "uniq_task_submission_outcome_version"
	index_name = "idx_task_submission_delivery_student"

	rows = frappe.db.sql(
		"SHOW INDEX FROM `{}`".format(table),
		as_dict=True,
	)

	if not _unique_index_exists(rows, ["task_outcome", "version"]):
		frappe.db.sql(
			f"ALTER TABLE `{table}` ADD UNIQUE INDEX `{unique_name}` (`task_outcome`, `version`)"
		)

	rows = frappe.db.sql(
		"SHOW INDEX FROM `{}`".format(table),
		as_dict=True,
	)
	if not _index_exists(rows, index_name):
		if _columns_exist(table, ["task_delivery", "student"]):
			frappe.db.sql(
				f"ALTER TABLE `{table}` ADD INDEX `{index_name}` (`task_delivery`, `student`)"
			)


def _unique_index_exists(rows, columns):
	index_map = {}
	for row in rows:
		key_name = row.get("Key_name")
		if not key_name:
			continue
		non_unique = row.get("Non_unique")
		try:
			non_unique = int(non_unique)
		except Exception:
			non_unique = 1
		if non_unique != 0:
			continue
		index_map.setdefault(key_name, []).append(row)

	for entries in index_map.values():
		ordered = sorted(entries, key=lambda r: int(r.get("Seq_in_index") or 0))
		cols = [row.get("Column_name") for row in ordered]
		if cols == columns:
			return True

	return False


def _index_exists(rows, index_name):
	return any(row.get("Key_name") == index_name for row in rows)


def _columns_exist(table, columns):
	rows = frappe.db.sql(
		"SHOW COLUMNS FROM `{}`".format(table),
		as_dict=True,
	)
	existing = {row.get("Field") for row in rows}
	return all(col in existing for col in columns)
