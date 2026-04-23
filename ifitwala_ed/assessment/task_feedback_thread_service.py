# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from ifitwala_ed.assessment.doctype.task_feedback_thread.task_feedback_thread import (
    LEARNER_STATES,
    TARGET_TYPES,
    THREAD_STATUSES,
    _build_thread_key,
)

MESSAGE_KINDS = ("reply", "clarification")
AUTHOR_ROLES = ("student", "instructor")


def build_feedback_thread_payloads(
    *,
    outcome_id: str | None = None,
    submission_id: str | None = None,
    workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    resolved_workspace_id = _resolve_workspace_id(
        outcome_id=outcome_id,
        submission_id=submission_id,
        workspace_id=workspace_id,
    )
    if not resolved_workspace_id:
        return []

    thread_rows = frappe.get_all(
        "Task Feedback Thread",
        filters={"task_feedback_workspace": resolved_workspace_id},
        fields=[
            "name",
            "target_type",
            "target_feedback_item",
            "target_priority",
            "summary_field",
            "learner_state",
            "thread_status",
            "modified",
            "modified_by",
        ],
        order_by="modified asc",
        limit=0,
    )
    if not thread_rows:
        return []

    thread_ids = [row.get("name") for row in thread_rows if row.get("name")]
    message_rows = frappe.get_all(
        "Task Feedback Thread Message",
        filters={
            "parent": ["in", thread_ids],
            "parenttype": "Task Feedback Thread",
            "parentfield": "messages",
        },
        fields=["name", "parent", "author", "author_role", "message_kind", "body", "creation"],
        order_by="parent asc, idx asc",
        limit=0,
    )
    messages_by_thread: dict[str, list[dict[str, Any]]] = {}
    for row in message_rows:
        parent = _clean_text(row.get("parent"))
        if not parent:
            continue
        messages_by_thread.setdefault(parent, []).append(
            {
                "id": row.get("name"),
                "author": _clean_text(row.get("author")),
                "author_role": _normalize_author_role(row.get("author_role")),
                "message_kind": _normalize_message_kind(row.get("message_kind")),
                "body": _clean_text(row.get("body")) or "",
                "created": row.get("creation"),
            }
        )

    return [
        {
            "thread_id": row.get("name"),
            "target_type": _normalize_target_type(row.get("target_type")),
            "target_feedback_item": _clean_text(row.get("target_feedback_item")),
            "target_priority": _clean_text(row.get("target_priority")),
            "summary_field": _clean_text(row.get("summary_field")),
            "learner_state": _normalize_learner_state(row.get("learner_state")),
            "thread_status": _normalize_thread_status(row.get("thread_status")),
            "messages": messages_by_thread.get(row.get("name"), []),
            "modified": row.get("modified"),
            "modified_by": _clean_text(row.get("modified_by")),
        }
        for row in thread_rows
    ]


def save_student_reply(payload: dict[str, Any] | str | None, *, actor: str | None = None) -> dict[str, Any]:
    data = _normalize_payload(payload)
    workspace_doc = _require_workspace_doc(data)
    thread_doc = _get_or_create_thread_doc(workspace_doc, data)
    thread_doc.thread_status = "open"
    thread_doc.append(
        "messages",
        {
            "author": actor or frappe.session.user,
            "author_role": "student",
            "message_kind": _normalize_message_kind(data.get("message_kind")),
            "body": _require_body(data.get("body")),
        },
    )
    _save_thread_doc(thread_doc)
    return _build_single_thread_payload(thread_doc.name)


def save_student_learner_state(payload: dict[str, Any] | str | None, *, actor: str | None = None) -> dict[str, Any]:
    data = _normalize_payload(payload)
    workspace_doc = _require_workspace_doc(data)
    thread_doc = _get_or_create_thread_doc(workspace_doc, data)
    thread_doc.learner_state = _normalize_learner_state(data.get("learner_state"))
    if not (thread_doc.get("messages") or []) and thread_doc.learner_state == "none":
        frappe.throw(_("Learner state updates require a learner state."))
    _save_thread_doc(thread_doc)
    return _build_single_thread_payload(thread_doc.name)


def save_instructor_reply(payload: dict[str, Any] | str | None, *, actor: str | None = None) -> dict[str, Any]:
    data = _normalize_payload(payload)
    thread_doc = _require_thread_doc(data)
    thread_doc.append(
        "messages",
        {
            "author": actor or frappe.session.user,
            "author_role": "instructor",
            "message_kind": "reply",
            "body": _require_body(data.get("body")),
        },
    )
    if _clean_text(data.get("thread_status")):
        thread_doc.thread_status = _normalize_thread_status(data.get("thread_status"))
    _save_thread_doc(thread_doc)
    return _build_single_thread_payload(thread_doc.name)


def save_instructor_thread_state(payload: dict[str, Any] | str | None, *, actor: str | None = None) -> dict[str, Any]:
    data = _normalize_payload(payload)
    thread_doc = _require_thread_doc(data)
    thread_doc.thread_status = _normalize_thread_status(data.get("thread_status"))
    if _clean_text(data.get("learner_state")):
        thread_doc.learner_state = _normalize_learner_state(data.get("learner_state"))
    _save_thread_doc(thread_doc)
    return _build_single_thread_payload(thread_doc.name)


def _build_single_thread_payload(thread_id: str) -> dict[str, Any]:
    rows = build_feedback_thread_payloads(
        workspace_id=_clean_text(frappe.db.get_value("Task Feedback Thread", thread_id, "task_feedback_workspace"))
    )
    for row in rows:
        if row.get("thread_id") == thread_id:
            return row
    frappe.throw(_("Feedback thread could not be loaded after saving."))


def _require_workspace_doc(data: dict[str, Any]):
    outcome_id = _clean_text(data.get("outcome_id") or data.get("task_outcome"))
    submission_id = _clean_text(data.get("submission_id") or data.get("task_submission"))
    if not outcome_id:
        frappe.throw(_("Task Outcome is required for feedback replies."))
    if not submission_id:
        frappe.throw(_("Task Submission is required for feedback replies."))
    workspace_name = frappe.db.get_value(
        "Task Feedback Workspace",
        {"task_outcome": outcome_id, "task_submission": submission_id},
        "name",
    )
    if not workspace_name:
        frappe.throw(_("No feedback workspace exists for this released submission version."), frappe.DoesNotExistError)
    return frappe.get_doc("Task Feedback Workspace", workspace_name)


def _require_thread_doc(data: dict[str, Any]):
    thread_id = _clean_text(data.get("thread_id"))
    if not thread_id:
        frappe.throw(_("thread_id is required."))
    return frappe.get_doc("Task Feedback Thread", thread_id)


def _resolve_workspace_id(
    *,
    outcome_id: str | None = None,
    submission_id: str | None = None,
    workspace_id: str | None = None,
) -> str | None:
    resolved_workspace_id = _clean_text(workspace_id)
    if resolved_workspace_id:
        return resolved_workspace_id
    resolved_outcome_id = _clean_text(outcome_id)
    resolved_submission_id = _clean_text(submission_id)
    if not resolved_outcome_id or not resolved_submission_id:
        return None
    db_get_value = getattr(getattr(frappe, "db", None), "get_value", None)
    if not callable(db_get_value):
        rows = frappe.get_all(
            "Task Feedback Workspace",
            filters={"task_outcome": resolved_outcome_id, "task_submission": resolved_submission_id},
            fields=["name"],
            order_by="modified desc, creation desc, name desc",
            limit=1,
        )
        if not rows:
            return None
        return _clean_text(rows[0].get("name"))
    return _clean_text(
        db_get_value(
            "Task Feedback Workspace",
            {"task_outcome": resolved_outcome_id, "task_submission": resolved_submission_id},
            "name",
        )
    )


def _get_or_create_thread_doc(workspace_doc, data: dict[str, Any]):
    target_type = _normalize_target_type(data.get("target_type"))
    target_feedback_item = _clean_text(data.get("target_feedback_item"))
    target_priority = _clean_text(data.get("target_priority"))
    summary_field = _clean_text(data.get("summary_field"))
    thread_key = _build_thread_key(
        target_type,
        target_feedback_item=target_feedback_item,
        target_priority=target_priority,
        summary_field=summary_field,
    )
    existing_name = frappe.db.get_value(
        "Task Feedback Thread",
        {"task_feedback_workspace": workspace_doc.name, "thread_key": thread_key},
        "name",
    )
    if existing_name:
        return frappe.get_doc("Task Feedback Thread", existing_name)
    doc = frappe.new_doc("Task Feedback Thread")
    doc.task_feedback_workspace = workspace_doc.name
    doc.target_type = target_type
    doc.target_feedback_item = target_feedback_item
    doc.target_priority = target_priority
    doc.summary_field = summary_field
    doc.learner_state = "none"
    doc.thread_status = "open"
    return doc


def _save_thread_doc(doc):
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)


def _normalize_payload(payload: dict[str, Any] | str | None) -> dict[str, Any]:
    if payload is None:
        frappe.throw(_("Payload must be a dict."))
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("Payload must be a dict."))
    return payload


def _normalize_target_type(value: Any) -> str:
    resolved = str(value or "feedback_item").strip().lower()
    if resolved not in TARGET_TYPES:
        frappe.throw(_("Unsupported feedback thread target type."))
    return resolved


def _normalize_learner_state(value: Any) -> str:
    resolved = str(value or "none").strip().lower()
    if resolved not in LEARNER_STATES:
        frappe.throw(_("Unsupported learner thread state."))
    return resolved


def _normalize_thread_status(value: Any) -> str:
    resolved = str(value or "open").strip().lower()
    if resolved not in THREAD_STATUSES:
        frappe.throw(_("Unsupported feedback thread status."))
    return resolved


def _normalize_message_kind(value: Any) -> str:
    resolved = str(value or "reply").strip().lower()
    if resolved not in MESSAGE_KINDS:
        frappe.throw(_("Unsupported feedback thread message kind."))
    return resolved


def _normalize_author_role(value: Any) -> str:
    resolved = str(value or "student").strip().lower()
    if resolved not in AUTHOR_ROLES:
        frappe.throw(_("Unsupported feedback thread author role."))
    return resolved


def _require_body(value: Any) -> str:
    resolved = _clean_text(value)
    if not resolved:
        frappe.throw(_("Reply text is required."))
    return resolved


def _clean_text(value: Any) -> str | None:
    resolved = str(value or "").strip()
    return resolved or None
