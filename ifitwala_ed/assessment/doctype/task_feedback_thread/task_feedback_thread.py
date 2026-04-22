# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

TARGET_TYPES = ("feedback_item", "priority", "summary")
LEARNER_STATES = ("none", "understood", "acted_on")
THREAD_STATUSES = ("open", "resolved")
SUMMARY_FIELDS = ("overall", "strengths", "improvements", "next_steps")
MESSAGE_KINDS = ("reply", "clarification")
AUTHOR_ROLES = ("student", "instructor")


class TaskFeedbackThread(Document):
    def before_validate(self):
        self._require_workspace()
        self._stamp_workspace_context()
        self._normalize_target_fields()
        self._normalize_state_fields()
        self._normalize_messages()

    def validate(self):
        self._validate_state_fields()
        self._validate_target_binding()
        self._validate_messages()
        self._require_activity()

    def _require_workspace(self):
        if not self.task_feedback_workspace:
            frappe.throw(_("Task Feedback Workspace is required."))

    def _get_workspace_context(self):
        if hasattr(self, "_workspace_row"):
            return self._workspace_row
        fields = [
            "task_outcome",
            "task_submission",
            "submission_version",
            "task_delivery",
            "task",
            "student",
            "student_group",
            "course",
            "academic_year",
            "school",
        ]
        row = frappe.db.get_value("Task Feedback Workspace", self.task_feedback_workspace, fields, as_dict=True)
        if not row:
            frappe.throw(_("Task Feedback Workspace not found."))
        self._workspace_row = row
        return row

    def _stamp_workspace_context(self):
        row = self._get_workspace_context()
        for field in (
            "task_outcome",
            "task_submission",
            "submission_version",
            "task_delivery",
            "task",
            "student",
            "student_group",
            "course",
            "academic_year",
            "school",
        ):
            if row.get(field) not in (None, ""):
                setattr(self, field, row.get(field))

    def _normalize_target_fields(self):
        self.target_type = str(self.target_type or "feedback_item").strip().lower()
        self.target_feedback_item = str(self.target_feedback_item or "").strip() or None
        self.target_priority = str(self.target_priority or "").strip() or None
        self.summary_field = str(self.summary_field or "").strip().lower() or None
        if self.target_type == "feedback_item":
            self.target_priority = None
            self.summary_field = None
            if not self.target_feedback_item:
                frappe.throw(_("Feedback threads targeting a feedback item require a feedback item id."))
        elif self.target_type == "priority":
            self.target_feedback_item = None
            self.summary_field = None
            if not self.target_priority:
                frappe.throw(_("Feedback threads targeting a priority require a priority id."))
        elif self.target_type == "summary":
            self.target_feedback_item = None
            self.target_priority = None
            if not self.summary_field:
                frappe.throw(_("Feedback threads targeting a summary section require a summary field."))
        else:
            frappe.throw(_("Unsupported feedback thread target type."))
        self.thread_key = _build_thread_key(
            self.target_type,
            target_feedback_item=self.target_feedback_item,
            target_priority=self.target_priority,
            summary_field=self.summary_field,
        )

    def _normalize_state_fields(self):
        self.learner_state = str(self.learner_state or "none").strip().lower()
        self.thread_status = str(self.thread_status or "open").strip().lower()

    def _normalize_messages(self):
        for row in self.get("messages") or []:
            row.author = str(row.author or "").strip() or frappe.session.user
            row.author_role = str(row.author_role or "").strip().lower()
            row.message_kind = str(row.message_kind or "reply").strip().lower()
            row.body = str(row.body or "").strip()

    def _validate_state_fields(self):
        if self.target_type not in TARGET_TYPES:
            frappe.throw(_("Unsupported feedback thread target type."))
        if self.learner_state not in LEARNER_STATES:
            frappe.throw(_("Unsupported learner thread state."))
        if self.thread_status not in THREAD_STATUSES:
            frappe.throw(_("Unsupported feedback thread status."))
        if self.summary_field and self.summary_field not in SUMMARY_FIELDS:
            frappe.throw(_("Unsupported summary field for feedback thread binding."))

    def _validate_target_binding(self):
        item_rows = frappe.get_all(
            "Task Feedback Item",
            filters={
                "parent": self.task_feedback_workspace,
                "parenttype": "Task Feedback Workspace",
                "parentfield": "feedback_items",
            },
            fields=["name"],
            limit=0,
        )
        item_ids = {row.get("name") for row in item_rows if row.get("name")}
        priority_rows = frappe.get_all(
            "Task Feedback Priority",
            filters={
                "parent": self.task_feedback_workspace,
                "parenttype": "Task Feedback Workspace",
                "parentfield": "priorities",
            },
            fields=["name"],
            limit=0,
        )
        priority_ids = {row.get("name") for row in priority_rows if row.get("name")}
        if self.target_type == "feedback_item" and self.target_feedback_item not in item_ids:
            frappe.throw(_("Feedback thread target item does not belong to the selected feedback workspace."))
        if self.target_type == "priority" and self.target_priority not in priority_ids:
            frappe.throw(_("Feedback thread target priority does not belong to the selected feedback workspace."))

    def _validate_messages(self):
        for row in self.get("messages") or []:
            if row.author_role not in AUTHOR_ROLES:
                frappe.throw(_("Unsupported feedback thread author role."))
            if row.message_kind not in MESSAGE_KINDS:
                frappe.throw(_("Unsupported feedback thread message kind."))
            if not row.body:
                frappe.throw(_("Feedback thread messages require body text."))

    def _require_activity(self):
        has_messages = bool(self.get("messages") or [])
        if not has_messages and self.learner_state == "none":
            frappe.throw(_("Feedback threads require at least one message or a learner action state."))


def on_doctype_update():
    _ensure_indexes()


def _ensure_indexes():
    table = "tabTask Feedback Thread"
    unique_name = "uniq_task_feedback_thread_workspace_key"
    submission_index = "idx_task_feedback_thread_submission"
    outcome_index = "idx_task_feedback_thread_outcome_modified"

    rows = frappe.db.sql(f"SHOW INDEX FROM `{table}`", as_dict=True)
    if not _unique_index_exists(rows, ["task_feedback_workspace", "thread_key"]):
        frappe.db.sql(
            f"ALTER TABLE `{table}` ADD UNIQUE INDEX `{unique_name}` (`task_feedback_workspace`, `thread_key`)"
        )

    rows = frappe.db.sql(f"SHOW INDEX FROM `{table}`", as_dict=True)
    if not _index_exists(rows, submission_index):
        frappe.db.sql(f"ALTER TABLE `{table}` ADD INDEX `{submission_index}` (`task_submission`)")

    rows = frappe.db.sql(f"SHOW INDEX FROM `{table}`", as_dict=True)
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


def _build_thread_key(
    target_type: str,
    *,
    target_feedback_item: str | None = None,
    target_priority: str | None = None,
    summary_field: str | None = None,
) -> str:
    if target_type == "feedback_item":
        return f"feedback_item::{target_feedback_item}"
    if target_type == "priority":
        return f"priority::{target_priority}"
    return f"summary::{summary_field}"
