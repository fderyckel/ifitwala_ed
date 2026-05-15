# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/gradebook.py

"""
Gradebook API public RPC boundary.

Public Frappe method paths remain locked on this module while implementation
ownership lives behind it:
- gradebook_reads.py
- gradebook_writes.py
- gradebook_support.py

Legacy staff gradebook endpoints remain here until the live SPA moves fully
onto the drawer-based canonical contract.
"""

from __future__ import annotations

import frappe

from ifitwala_ed.api import gradebook_reads, gradebook_support, gradebook_writes, outcome_publish


@frappe.whitelist()
def get_grid(filters=None, **kwargs):
    return gradebook_reads.get_grid(gradebook_support, filters=filters, **kwargs)


@frappe.whitelist()
def get_drawer(outcome_id: str, submission_id: str | None = None, version: int | str | None = None):
    return gradebook_reads.get_drawer(
        gradebook_support,
        outcome_id,
        submission_id=submission_id,
        version=version,
    )


@frappe.whitelist()
def save_draft(payload=None, **kwargs):
    return gradebook_writes.save_draft(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def save_feedback_draft(payload=None, **kwargs):
    return gradebook_writes.save_feedback_draft(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def save_feedback_publication(payload=None, **kwargs):
    return gradebook_writes.save_feedback_publication(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def save_feedback_comment_bank_entry(payload=None, **kwargs):
    return gradebook_writes.save_feedback_comment_bank_entry(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def save_feedback_thread_reply(payload=None, **kwargs):
    return gradebook_writes.save_feedback_thread_reply(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def save_feedback_thread_state(payload=None, **kwargs):
    return gradebook_writes.save_feedback_thread_state(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def export_feedback_pdf(payload=None, **kwargs):
    return gradebook_writes.export_feedback_pdf(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def submit_contribution(payload=None, **kwargs):
    return gradebook_writes.submit_contribution(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def save_contribution_draft(payload=None, **kwargs):
    return save_draft(payload=payload, **kwargs)


@frappe.whitelist()
def moderator_action(payload=None, **kwargs):
    return gradebook_writes.moderator_action(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def mark_new_submission_seen(outcome: str):
    return gradebook_writes.mark_new_submission_seen(gradebook_support, outcome)


@frappe.whitelist()
def fetch_groups(
    search: str | None = None,
    limit: int | None = None,
    school: str | None = None,
    academic_year: str | None = None,
    program: str | None = None,
    course: str | None = None,
):
    return gradebook_reads.fetch_groups(
        gradebook_support,
        search=search,
        limit=limit,
        school=school,
        academic_year=academic_year,
        program=program,
        course=course,
    )


@frappe.whitelist()
def fetch_group_tasks(student_group: str):
    return gradebook_reads.fetch_group_tasks(gradebook_support, student_group)


@frappe.whitelist()
def get_task_gradebook(task: str):
    return gradebook_reads.get_task_gradebook(gradebook_support, task)


@frappe.whitelist()
def get_task_quiz_manual_review(
    task: str, view_mode: str | None = None, quiz_question: str | None = None, student: str | None = None
):
    return gradebook_reads.get_task_quiz_manual_review(
        gradebook_support,
        task,
        view_mode=view_mode,
        quiz_question=quiz_question,
        student=student,
    )


@frappe.whitelist()
def save_task_quiz_manual_review(task: str, grades=None, **kwargs):
    return gradebook_writes.save_task_quiz_manual_review(gradebook_support, task, grades=grades, **kwargs)


@frappe.whitelist()
def update_task_student(task_student: str, updates=None, **kwargs):
    return gradebook_writes.update_task_student(gradebook_support, task_student, updates=updates, **kwargs)


@frappe.whitelist()
def batch_mark_completion(payload=None, **kwargs):
    return gradebook_writes.batch_mark_completion(gradebook_support, payload=payload, **kwargs)


@frappe.whitelist()
def publish_outcomes(payload=None, **kwargs):
    return outcome_publish.publish_outcomes(payload=payload, **kwargs)


@frappe.whitelist()
def unpublish_outcomes(payload=None, **kwargs):
    return outcome_publish.unpublish_outcomes(payload=payload, **kwargs)


__all__ = [
    "get_grid",
    "get_drawer",
    "save_draft",
    "save_feedback_draft",
    "save_feedback_publication",
    "save_feedback_comment_bank_entry",
    "save_feedback_thread_reply",
    "save_feedback_thread_state",
    "export_feedback_pdf",
    "submit_contribution",
    "save_contribution_draft",
    "moderator_action",
    "mark_new_submission_seen",
    "fetch_groups",
    "fetch_group_tasks",
    "get_task_gradebook",
    "get_task_quiz_manual_review",
    "save_task_quiz_manual_review",
    "update_task_student",
    "batch_mark_completion",
    "publish_outcomes",
    "unpublish_outcomes",
]
