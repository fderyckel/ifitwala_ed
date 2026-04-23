# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.assessment.task_feedback_comment_bank_service import (
    COMMENT_BANK_SCOPE_MODES,
)
from ifitwala_ed.assessment.task_feedback_service import FEEDBACK_INTENT_OPTIONS


class TaskFeedbackCommentBankEntry(Document):
    def before_validate(self):
        self.entry_label = (self.entry_label or "").strip()
        self.body = (self.body or "").strip()
        self.feedback_intent = str(self.feedback_intent or "issue").strip().lower()
        self.scope_mode = str(self.scope_mode or "course").strip().lower()
        self.assessment_criteria = (self.assessment_criteria or "").strip() or None
        self.course = (self.course or "").strip() or None
        self.task = (self.task or "").strip() or None
        self.is_active = 1 if int(self.is_active or 0) else 0
        if not self.entry_label and self.body:
            collapsed = " ".join(self.body.split())
            self.entry_label = collapsed[:120] if len(collapsed) <= 120 else "{0}…".format(collapsed[:119].rstrip())

    def validate(self):
        if not self.body:
            frappe.throw(_("Reusable comment text is required."))
        if not self.entry_label:
            frappe.throw(_("Reusable comment label is required."))
        if self.feedback_intent not in FEEDBACK_INTENT_OPTIONS:
            frappe.throw(_("Invalid reusable comment intent."))
        if self.scope_mode not in COMMENT_BANK_SCOPE_MODES:
            frappe.throw(_("Invalid reusable comment scope."))
        self._validate_scope_context()

    def _validate_scope_context(self):
        if self.scope_mode == "personal":
            self.course = None
            self.task = None
            return

        if not self.course:
            frappe.throw(_("Course is required for course- or task-scoped reusable comments."))

        if self.scope_mode == "course":
            self.task = None
            return

        if not self.task:
            frappe.throw(_("Task is required for task-scoped reusable comments."))

        task_course = frappe.db.get_value("Task", self.task, "default_course")
        if task_course and task_course != self.course:
            frappe.throw(_("Task-scoped reusable comments must match the selected task course."))


def on_doctype_update():
    _ensure_indexes()


def _ensure_indexes():
    table = "tabTask Feedback Comment Bank Entry"
    owner_active_index = "idx_tfcbe_owner_active_modified"

    rows = frappe.db.sql("SHOW INDEX FROM `{}`".format(table), as_dict=True)
    if not _index_exists(rows, owner_active_index):
        frappe.db.sql(f"ALTER TABLE `{table}` ADD INDEX `{owner_active_index}` (`owner`, `is_active`, `modified`)")


def _index_exists(rows, index_name):
    return any(row.get("Key_name") == index_name for row in rows)
