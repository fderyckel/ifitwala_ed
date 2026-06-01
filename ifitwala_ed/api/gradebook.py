# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/gradebook.py

"""
Gradebook API public RPC boundary.

Public Frappe method paths remain locked on this module while implementation
ownership lives behind it:
- ifitwala_ed.assessment.api.gradebook.endpoints
- ifitwala_ed.assessment.api.gradebook.reads
- ifitwala_ed.assessment.api.gradebook.writes
- ifitwala_ed.assessment.api.gradebook.support

Legacy staff gradebook endpoints remain here until the live SPA moves fully
onto the drawer-based canonical contract.
"""

from __future__ import annotations

from ifitwala_ed.assessment.api.gradebook.endpoints import (
    batch_mark_completion,
    export_feedback_pdf,
    fetch_group_tasks,
    fetch_groups,
    get_drawer,
    get_grid,
    get_task_gradebook,
    get_task_quiz_manual_review,
    mark_new_submission_seen,
    moderator_action,
    publish_outcomes,
    save_contribution_draft,
    save_draft,
    save_feedback_comment_bank_entry,
    save_feedback_draft,
    save_feedback_publication,
    save_feedback_thread_reply,
    save_feedback_thread_state,
    save_task_quiz_manual_review,
    submit_contribution,
    unpublish_outcomes,
    update_task_student,
)

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
