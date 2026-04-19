# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from ifitwala_ed.assessment.task_feedback_service import FEEDBACK_INTENT_OPTIONS

COMMENT_BANK_SCOPE_MODES = ("personal", "course", "task")
COMMENT_BANK_LIMIT = 50


def build_comment_bank_payload(outcome_id: str, *, actor: str | None = None) -> dict[str, Any]:
    actor = actor or frappe.session.user
    context = _get_outcome_context(outcome_id)
    criteria_map = _get_delivery_criteria_map(context.get("task_delivery"))

    rows = frappe.get_all(
        "Task Feedback Comment Bank Entry",
        filters={"owner": actor, "is_active": 1},
        fields=[
            "name",
            "entry_label",
            "body",
            "feedback_intent",
            "scope_mode",
            "course",
            "task",
            "assessment_criteria",
            "modified",
        ],
        order_by="modified desc",
        limit=COMMENT_BANK_LIMIT,
    )

    entries = []
    for row in rows or []:
        normalized = _serialize_comment_bank_entry(row, context=context, criteria_map=criteria_map)
        if normalized:
            entries.append(normalized)

    entries.sort(
        key=lambda row: (
            -int(row.get("match_score") or 0),
            row.get("label") or "",
        )
    )

    return {
        "context": {
            "course": context.get("course"),
            "task": context.get("task"),
            "task_title": context.get("task_title"),
            "criteria": [
                {
                    "assessment_criteria": criteria_name,
                    "criteria_name": criteria_row.get("criteria_name") or criteria_name,
                }
                for criteria_name, criteria_row in criteria_map.items()
            ],
        },
        "entries": entries,
    }


def save_comment_bank_entry(payload: dict[str, Any] | str | None, *, actor: str | None = None) -> dict[str, Any]:
    actor = actor or frappe.session.user
    data = _normalize_payload(payload)
    outcome_id = _clean_text(data.get("outcome_id") or data.get("task_outcome"))
    if not outcome_id:
        frappe.throw(_("Task Outcome is required for comment-bank updates."))

    context = _get_outcome_context(outcome_id)
    entry_id = _clean_text(data.get("entry_id") or data.get("id"))
    scope_mode = _normalize_scope_mode(data.get("scope_mode"))
    body = _clean_text(data.get("body"))
    if not body:
        frappe.throw(_("Reusable comment text is required."))

    assessment_criteria = _clean_text(data.get("assessment_criteria"))
    criteria_map = _get_delivery_criteria_map(context.get("task_delivery"))
    if assessment_criteria and assessment_criteria not in criteria_map:
        frappe.throw(_("Reusable comments may only link to criteria active on this delivery."))

    doc = _get_or_create_entry_doc(entry_id, actor=actor)
    doc.entry_label = _derive_entry_label(_clean_text(data.get("label")), body)
    doc.body = body
    doc.feedback_intent = _normalize_feedback_intent(data.get("feedback_intent"))
    doc.scope_mode = scope_mode
    doc.assessment_criteria = assessment_criteria or None
    doc.is_active = _normalize_is_active(data.get("is_active"))
    _stamp_scope(doc, context=context, scope_mode=scope_mode)

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    return build_comment_bank_payload(outcome_id, actor=actor)


def _normalize_payload(payload: dict[str, Any] | str | None) -> dict[str, Any]:
    if payload in (None, "", {}):
        return {}
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("Comment-bank payload must be an object."))
    return payload


def _get_outcome_context(outcome_id: str) -> dict[str, Any]:
    outcome = frappe.db.get_value(
        "Task Outcome",
        outcome_id,
        ["name", "task_delivery", "task", "course"],
        as_dict=True,
    )
    if not outcome:
        frappe.throw(_("Task Outcome not found."))

    task_title = None
    task_id = _clean_text(outcome.get("task"))
    if task_id:
        task_row = frappe.db.get_value("Task", task_id, ["name", "title", "default_course"], as_dict=True) or {}
        task_title = _clean_text(task_row.get("title"))
        if not outcome.get("course") and task_row.get("default_course"):
            outcome["course"] = task_row.get("default_course")

    return {
        "task_outcome": outcome_id,
        "task_delivery": _clean_text(outcome.get("task_delivery")),
        "task": task_id,
        "task_title": task_title,
        "course": _clean_text(outcome.get("course")),
    }


def _get_delivery_criteria_map(task_delivery: str | None) -> dict[str, dict[str, Any]]:
    delivery_id = _clean_text(task_delivery)
    if not delivery_id:
        return {}

    delivery = frappe.db.get_value(
        "Task Delivery",
        delivery_id,
        ["name", "grading_mode", "rubric_version"],
        as_dict=True,
    )
    if not delivery or _clean_text(delivery.get("grading_mode")) != "Criteria":
        return {}

    rubric_version = _clean_text(delivery.get("rubric_version"))
    if not rubric_version:
        return {}

    rows = frappe.get_all(
        "Task Rubric Criterion",
        filters={
            "parent": rubric_version,
            "parenttype": "Task Rubric Version",
            "parentfield": "criteria",
        },
        fields=["assessment_criteria", "criteria_name"],
        order_by="idx asc",
        limit=0,
    )

    out: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        criteria_name = _clean_text(row.get("assessment_criteria"))
        if not criteria_name:
            continue
        out[criteria_name] = {
            "criteria_name": _clean_text(row.get("criteria_name")) or criteria_name,
        }
    return out


def _serialize_comment_bank_entry(
    row: dict[str, Any], *, context: dict[str, Any], criteria_map: dict[str, dict[str, Any]]
):
    scope_mode = _normalize_scope_mode(row.get("scope_mode"))
    course = _clean_text(row.get("course"))
    task = _clean_text(row.get("task"))
    assessment_criteria = _clean_text(row.get("assessment_criteria"))

    if scope_mode == "course" and course and course != context.get("course"):
        return None
    if scope_mode == "task" and task and task != context.get("task"):
        return None
    if assessment_criteria and assessment_criteria not in criteria_map:
        return None

    match_reasons = []
    match_score = 0
    if scope_mode == "task" and task and task == context.get("task"):
        match_reasons.append("task")
        match_score += 4
    elif scope_mode == "course" and course and course == context.get("course"):
        match_reasons.append("course")
        match_score += 2
    else:
        match_reasons.append("personal")
        match_score += 1

    criteria_label = None
    if assessment_criteria:
        criteria_label = (criteria_map.get(assessment_criteria) or {}).get("criteria_name") or assessment_criteria
        if criteria_label:
            match_reasons.append("criterion")
            match_score += 3

    return {
        "id": row.get("name"),
        "label": _clean_text(row.get("entry_label")) or _derive_entry_label("", _clean_text(row.get("body"))),
        "body": _clean_text(row.get("body")),
        "intent": _normalize_feedback_intent(row.get("feedback_intent")),
        "scope_mode": scope_mode,
        "course": course or None,
        "task": task or None,
        "assessment_criteria": assessment_criteria or None,
        "assessment_criteria_label": criteria_label or None,
        "match_reasons": match_reasons,
        "match_score": match_score,
    }


def _get_or_create_entry_doc(entry_id: str, *, actor: str):
    entry_name = _clean_text(entry_id)
    if not entry_name:
        return frappe.new_doc("Task Feedback Comment Bank Entry")

    doc = frappe.get_doc("Task Feedback Comment Bank Entry", entry_name)
    if _clean_text(getattr(doc, "owner", "")) != actor:
        frappe.throw(_("You can only update your own reusable feedback comments."), frappe.PermissionError)
    return doc


def _stamp_scope(doc, *, context: dict[str, Any], scope_mode: str) -> None:
    if scope_mode == "personal":
        doc.course = None
        doc.task = None
        return
    doc.course = context.get("course") or None
    doc.task = context.get("task") if scope_mode == "task" else None


def _normalize_scope_mode(value: Any) -> str:
    resolved = _clean_text(value).lower() or "course"
    if resolved not in COMMENT_BANK_SCOPE_MODES:
        frappe.throw(_("Invalid reusable comment scope."))
    return resolved


def _normalize_feedback_intent(value: Any) -> str:
    resolved = _clean_text(value).lower() or "issue"
    if resolved not in FEEDBACK_INTENT_OPTIONS:
        frappe.throw(_("Invalid reusable comment intent."))
    return resolved


def _normalize_is_active(value: Any) -> int:
    if value in (None, "", True, 1, "1", "true", "True"):
        return 1
    if value in (False, 0, "0", "false", "False"):
        return 0
    return 1


def _derive_entry_label(label: str, body: str) -> str:
    explicit = _clean_text(label)
    if explicit:
        return explicit[:120]
    collapsed = " ".join(_clean_text(body).split())
    if not collapsed:
        frappe.throw(_("Reusable comments need a label or body text."))
    if len(collapsed) <= 72:
        return collapsed
    return "{0}…".format(collapsed[:71].rstrip())


def _clean_text(value: Any) -> str:
    return str(value or "").strip()
