# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.assessment.task_feedback_service import (
    FEEDBACK_INTENT_OPTIONS,
    FEEDBACK_ITEM_KINDS,
    FEEDBACK_WORKFLOW_STATES,
    PUBLICATION_VISIBILITY_STATES,
    normalize_feedback_anchor_payload,
)


class TaskFeedbackWorkspace(Document):
    def before_validate(self):
        self._require_links()
        outcome = self._get_outcome_context()
        self._stamp_context(outcome)
        self._ensure_submission_matches_outcome()
        self._set_submission_version()
        self._normalize_publication_fields()
        self._normalize_feedback_items()

    def validate(self):
        self._validate_publication_fields()
        self._validate_feedback_items()

    def _doc_meta(self):
        if not hasattr(self, "_workspace_meta"):
            self._workspace_meta = frappe.get_meta(self.doctype)
        return self._workspace_meta

    def _has_field(self, fieldname):
        return bool(self._doc_meta().get_field(fieldname))

    def _require_links(self):
        if not self.task_outcome:
            frappe.throw(_("Task Outcome is required."))
        if not self.task_submission:
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
        ]
        outcome = frappe.db.get_value("Task Outcome", self.task_outcome, fields, as_dict=True)
        if not outcome:
            frappe.throw(_("Task Outcome not found."))
        self._outcome_row = outcome
        return outcome

    def _stamp_context(self, outcome):
        for field in ("task_delivery", "task", "student", "student_group", "course", "academic_year", "school"):
            if self._has_field(field) and outcome.get(field):
                setattr(self, field, outcome.get(field))

    def _ensure_submission_matches_outcome(self):
        fields = ["task_outcome", "version"]
        submission = frappe.db.get_value("Task Submission", self.task_submission, fields, as_dict=True)
        if not submission:
            frappe.throw(_("Task Submission not found."))
        if submission.get("task_outcome") != self.task_outcome:
            frappe.throw(_("Task Submission does not belong to the selected Task Outcome."))
        self._submission_row = submission

    def _set_submission_version(self):
        submission = getattr(self, "_submission_row", None) or {}
        try:
            self.submission_version = int(submission.get("version") or 0)
        except Exception:
            self.submission_version = 0
        if not self.submission_version:
            frappe.throw(_("Task Submission version is required for feedback binding."))

    def _normalize_publication_fields(self):
        self.feedback_visibility = str(self.feedback_visibility or "hidden").strip().lower()
        self.grade_visibility = str(self.grade_visibility or "hidden").strip().lower()

    def _validate_publication_fields(self):
        for fieldname in ("feedback_visibility", "grade_visibility"):
            value = str(getattr(self, fieldname, "") or "").strip().lower()
            if value not in PUBLICATION_VISIBILITY_STATES:
                frappe.throw(_("Invalid visibility state for {0}.").format(fieldname.replace("_", " ")))

    def _normalize_feedback_items(self):
        for row in self.get("feedback_items") or []:
            row.anchor_kind = str(row.anchor_kind or "").strip().lower()
            row.feedback_intent = str(row.feedback_intent or "issue").strip().lower()
            row.workflow_state = str(row.workflow_state or "draft").strip().lower()
            row.body = (row.body or "").strip()
            if not row.author:
                row.author = frappe.session.user
            row.anchor_payload = json.dumps(
                normalize_feedback_anchor_payload(
                    row.anchor_kind,
                    row.page_number,
                    row.anchor_payload,
                ),
                separators=(",", ":"),
                sort_keys=True,
            )

    def _validate_feedback_items(self):
        for row in self.get("feedback_items") or []:
            if row.anchor_kind not in FEEDBACK_ITEM_KINDS:
                frappe.throw(_("Invalid anchor kind on a feedback item."))
            if row.feedback_intent not in FEEDBACK_INTENT_OPTIONS:
                frappe.throw(_("Invalid feedback intent on a feedback item."))
            if row.workflow_state not in FEEDBACK_WORKFLOW_STATES:
                frappe.throw(_("Invalid workflow state on a feedback item."))
            try:
                page_number = int(row.page_number or 0)
            except Exception:
                page_number = 0
            if page_number <= 0:
                frappe.throw(_("Feedback item page number must be a positive integer."))
            normalize_feedback_anchor_payload(row.anchor_kind, page_number, row.anchor_payload)


def on_doctype_update():
    _ensure_indexes()


def _ensure_indexes():
    table = "tabTask Feedback Workspace"
    unique_name = "uniq_task_feedback_workspace_outcome_submission"
    submission_index = "idx_task_feedback_workspace_submission"
    outcome_index = "idx_task_feedback_workspace_outcome_modified"

    rows = frappe.db.sql("SHOW INDEX FROM `{}`".format(table), as_dict=True)
    if not _unique_index_exists(rows, ["task_outcome", "task_submission"]):
        frappe.db.sql(f"ALTER TABLE `{table}` ADD UNIQUE INDEX `{unique_name}` (`task_outcome`, `task_submission`)")

    rows = frappe.db.sql("SHOW INDEX FROM `{}`".format(table), as_dict=True)
    if not _index_exists(rows, submission_index):
        frappe.db.sql(f"ALTER TABLE `{table}` ADD INDEX `{submission_index}` (`task_submission`)")

    rows = frappe.db.sql("SHOW INDEX FROM `{}`".format(table), as_dict=True)
    if not _index_exists(rows, outcome_index):
        frappe.db.sql(f"ALTER TABLE `{table}` ADD INDEX `{outcome_index}` (`task_outcome`, `modified`)")


def _unique_index_exists(rows, columns):
    index_map = {}
    for row in rows:
        key_name = row.get("Key_name")
        if not key_name:
            continue
        try:
            non_unique = int(row.get("Non_unique") or 1)
        except Exception:
            non_unique = 1
        if non_unique != 0:
            continue
        index_map.setdefault(key_name, []).append(row)

    for entries in index_map.values():
        ordered = sorted(entries, key=lambda row: int(row.get("Seq_in_index") or 0))
        if [row.get("Column_name") for row in ordered] == columns:
            return True
    return False


def _index_exists(rows, index_name):
    return any(row.get("Key_name") == index_name for row in rows)
