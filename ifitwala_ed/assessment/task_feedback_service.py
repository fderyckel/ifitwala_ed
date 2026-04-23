# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

PUBLICATION_VISIBILITY_STATES = ("hidden", "student", "student_and_guardian")
FEEDBACK_ITEM_KINDS = ("point", "rect", "page", "text_quote", "path")
FEEDBACK_INTENT_OPTIONS = ("strength", "issue", "question", "next_step", "rubric_evidence")
FEEDBACK_WORKFLOW_STATES = ("draft", "published", "acknowledged", "resolved")
PUBLICATION_AUDIENCES = ("student", "guardian")
SUMMARY_FIELDS = ("overall", "strengths", "improvements", "next_steps")
WORKSPACE_READ_COLUMNS = (
    "feedback_visibility",
    "grade_visibility",
    "overall_summary",
    "strengths_summary",
    "improvements_summary",
    "next_steps_summary",
)
FEEDBACK_ITEM_READ_COLUMNS = (
    "anchor_kind",
    "page_number",
    "feedback_intent",
    "workflow_state",
    "body",
    "anchor_payload",
    "assessment_criteria",
    "author",
)
FEEDBACK_PRIORITY_READ_COLUMNS = ("title", "detail", "feedback_item_id", "assessment_criteria")
FEEDBACK_THREAD_READ_COLUMNS = (
    "task_feedback_workspace",
    "target_type",
    "target_feedback_item",
    "target_priority",
    "summary_field",
    "learner_state",
    "thread_status",
)
FEEDBACK_THREAD_MESSAGE_READ_COLUMNS = ("author", "author_role", "message_kind", "body")


def build_feedback_workspace_payload(
    outcome_id: str, submission_id: str, *, include_defaults: bool = True
) -> dict[str, Any] | None:
    submission = _require_feedback_submission_context(outcome_id, submission_id)
    legacy_release = _get_legacy_release_state(outcome_id)
    workspace_row = None
    if _feedback_workspace_reads_available():
        workspace_row = frappe.db.get_value(
            "Task Feedback Workspace",
            {"task_outcome": outcome_id, "task_submission": submission_id},
            [
                "name",
                "feedback_visibility",
                "grade_visibility",
                "overall_summary",
                "strengths_summary",
                "improvements_summary",
                "next_steps_summary",
                "modified",
                "modified_by",
            ],
            as_dict=True,
        )

    if not workspace_row and not include_defaults:
        return None

    feedback_items = []
    priorities = []
    if workspace_row and workspace_row.get("name"):
        if _feedback_item_reads_available():
            feedback_items = _load_feedback_item_rows(workspace_row.get("name"))
        if _feedback_priority_reads_available():
            priorities = _load_feedback_priority_rows(workspace_row.get("name"))

    derived_from_legacy = not bool(workspace_row)
    feedback_visibility, grade_visibility = _resolve_publication_defaults(workspace_row, legacy_release)
    return {
        "workspace_id": (workspace_row or {}).get("name"),
        "task_outcome": outcome_id,
        "task_submission": submission_id,
        "submission_version": submission.get("version"),
        "summary": {
            "overall": (workspace_row or {}).get("overall_summary") or "",
            "strengths": (workspace_row or {}).get("strengths_summary") or "",
            "improvements": (workspace_row or {}).get("improvements_summary") or "",
            "next_steps": (workspace_row or {}).get("next_steps_summary") or "",
        },
        "priorities": priorities,
        "items": feedback_items,
        "publication": {
            "feedback_visibility": feedback_visibility,
            "grade_visibility": grade_visibility,
            "derived_from_legacy_outcome": derived_from_legacy,
            "legacy_outcome_published": bool(int(legacy_release.get("is_published") or 0)),
            "legacy_published_on": legacy_release.get("published_on"),
            "legacy_published_by": legacy_release.get("published_by"),
        },
        "modified": (workspace_row or {}).get("modified"),
        "modified_by": (workspace_row or {}).get("modified_by"),
    }


def publication_visible_to_audience(visibility: str | None, audience: str = "student") -> bool:
    resolved_visibility = _normalize_visibility_state(visibility)
    resolved_audience = _normalize_publication_audience(audience)
    if resolved_audience == "student":
        return resolved_visibility in ("student", "student_and_guardian")
    return resolved_visibility == "student_and_guardian"


def build_released_result_payload(
    outcome_id: str,
    *,
    audience: str = "student",
    submission_id: str | None = None,
) -> dict[str, Any]:
    resolved_audience = _normalize_publication_audience(audience)
    outcome = _get_released_result_outcome_context(outcome_id)
    resolved_submission_id = _resolve_submission_context_for_release(outcome_id, submission_id)
    workspace_payload = (
        build_feedback_workspace_payload(outcome_id, resolved_submission_id) if resolved_submission_id else None
    )

    publication = (
        dict(workspace_payload.get("publication") or {})
        if workspace_payload
        else _publication_payload_from_legacy(outcome)
    )
    feedback_visible = publication_visible_to_audience(publication.get("feedback_visibility"), resolved_audience)
    grade_visible = publication_visible_to_audience(publication.get("grade_visibility"), resolved_audience)

    summary = {
        "overall": "",
        "strengths": "",
        "improvements": "",
        "next_steps": "",
    }
    items: list[dict[str, Any]] = []
    submission_version = None
    modified = None
    modified_by = None
    if feedback_visible and workspace_payload:
        summary = {
            "overall": _clean_text((workspace_payload.get("summary") or {}).get("overall")) or "",
            "strengths": _clean_text((workspace_payload.get("summary") or {}).get("strengths")) or "",
            "improvements": _clean_text((workspace_payload.get("summary") or {}).get("improvements")) or "",
            "next_steps": _clean_text((workspace_payload.get("summary") or {}).get("next_steps")) or "",
        }
        items = list(workspace_payload.get("items") or [])
        submission_version = workspace_payload.get("submission_version")
        modified = workspace_payload.get("modified")
        modified_by = workspace_payload.get("modified_by")

    official_feedback = _clean_text(outcome.get("official_feedback"))
    if feedback_visible and not any(summary.values()) and official_feedback:
        summary["overall"] = official_feedback

    return {
        "outcome_id": outcome_id,
        "task_submission": resolved_submission_id,
        "grade_visible": grade_visible,
        "feedback_visible": feedback_visible,
        "publication": {
            "feedback_visibility": publication.get("feedback_visibility") or "hidden",
            "grade_visibility": publication.get("grade_visibility") or "hidden",
            "derived_from_legacy_outcome": bool(publication.get("derived_from_legacy_outcome")),
            "legacy_outcome_published": bool(publication.get("legacy_outcome_published")),
            "legacy_published_on": publication.get("legacy_published_on"),
            "legacy_published_by": publication.get("legacy_published_by"),
        },
        "official": {
            "score": outcome.get("official_score") if grade_visible else None,
            "grade": _clean_text(outcome.get("official_grade")) if grade_visible else None,
            "grade_value": outcome.get("official_grade_value") if grade_visible else None,
            "feedback": official_feedback if feedback_visible else None,
        },
        "feedback": (
            {
                "task_submission": resolved_submission_id,
                "submission_version": submission_version,
                "summary": summary,
                "items": items,
                "modified": modified,
                "modified_by": modified_by,
            }
            if feedback_visible
            else None
        ),
    }


def build_released_feedback_detail_payload(
    outcome_id: str,
    *,
    audience: str = "student",
    submission_id: str | None = None,
) -> dict[str, Any]:
    from ifitwala_ed.assessment import task_feedback_thread_service

    released = build_released_result_payload(
        outcome_id,
        audience=audience,
        submission_id=submission_id,
    )
    if not released.get("grade_visible") and not released.get("feedback_visible"):
        frappe.throw(_("Released feedback is not available for this audience."), frappe.PermissionError)

    resolved_audience = _normalize_publication_audience(audience)
    resolved_submission_id = _clean_text(released.get("task_submission"))
    workspace_payload = (
        build_feedback_workspace_payload(outcome_id, resolved_submission_id) if resolved_submission_id else None
    )
    outcome_context = _get_release_context(outcome_id)
    released_items = list((released.get("feedback") or {}).get("items") or [])
    released_priorities = (
        list((workspace_payload or {}).get("priorities") or []) if released.get("feedback_visible") else []
    )
    feedback_threads = (
        task_feedback_thread_service.build_feedback_thread_payloads(
            outcome_id=outcome_id,
            submission_id=resolved_submission_id,
        )
        if (
            resolved_audience == "student"
            and released.get("feedback_visible")
            and resolved_submission_id
            and _feedback_thread_reads_available()
        )
        else []
    )
    return {
        "outcome_id": outcome_id,
        "audience": resolved_audience,
        "context": outcome_context,
        "task_submission": resolved_submission_id,
        "grade_visible": bool(released.get("grade_visible")),
        "feedback_visible": bool(released.get("feedback_visible")),
        "publication": dict(released.get("publication") or {}),
        "official": dict(released.get("official") or {}),
        "feedback": (
            {
                "task_submission": resolved_submission_id,
                "submission_version": (released.get("feedback") or {}).get("submission_version"),
                "summary": dict((released.get("feedback") or {}).get("summary") or {}),
                "priorities": released_priorities,
                "items": released_items,
                "rubric_snapshot": _build_released_rubric_snapshot(
                    outcome_id,
                    released_items,
                    grade_visible=bool(released.get("grade_visible")),
                    feedback_visible=bool(released.get("feedback_visible")),
                ),
                "threads": feedback_threads,
                "modified": (released.get("feedback") or {}).get("modified"),
                "modified_by": (released.get("feedback") or {}).get("modified_by"),
            }
            if released.get("feedback_visible")
            else None
        ),
        "allowed_actions": {
            "can_reply": resolved_audience == "student" and bool(released.get("feedback_visible")),
            "can_set_learner_state": resolved_audience == "student" and bool(released.get("feedback_visible")),
            "can_view_threads": resolved_audience == "student" and bool(released.get("feedback_visible")),
        },
    }


def save_feedback_workspace_draft(payload: dict[str, Any] | str | None, *, actor: str | None = None) -> dict[str, Any]:
    data = _normalize_payload(payload)
    outcome_id = _clean_text(data.get("outcome_id") or data.get("task_outcome"))
    submission_id = _clean_text(data.get("submission_id") or data.get("task_submission"))
    if not outcome_id:
        frappe.throw(_("Task Outcome is required for feedback drafts."))
    if not submission_id:
        frappe.throw(_("Task Submission is required for feedback drafts."))

    actor = actor or frappe.session.user
    _require_feedback_submission_context(outcome_id, submission_id)
    workspace_doc = _get_or_create_workspace_doc(outcome_id, submission_id)

    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    workspace_doc.overall_summary = _clean_text(summary.get("overall"))
    workspace_doc.strengths_summary = _clean_text(summary.get("strengths"))
    workspace_doc.improvements_summary = _clean_text(summary.get("improvements"))
    workspace_doc.next_steps_summary = _clean_text(summary.get("next_steps"))

    next_items = []
    for raw_item in _coerce_items(data.get("items")):
        next_items.append(_normalize_feedback_item_record(raw_item, actor=actor))
    _replace_child_rows_preserving_names(
        workspace_doc,
        "feedback_items",
        next_items,
        id_key="id",
    )

    next_priorities = []
    for raw_priority in _coerce_priorities(data.get("priorities")):
        next_priorities.append(_normalize_feedback_priority_record(raw_priority))
    _replace_child_rows_preserving_names(
        workspace_doc,
        "priorities",
        next_priorities,
        id_key="id",
    )

    _save_workspace_doc(workspace_doc)
    return build_feedback_workspace_payload(outcome_id, submission_id) or {}


def save_feedback_publication(payload: dict[str, Any] | str | None, *, actor: str | None = None) -> dict[str, Any]:
    data = _normalize_payload(payload)
    outcome_id = _clean_text(data.get("outcome_id") or data.get("task_outcome"))
    submission_id = _clean_text(data.get("submission_id") or data.get("task_submission"))
    if not outcome_id:
        frappe.throw(_("Task Outcome is required for publication changes."))
    if not submission_id:
        frappe.throw(_("Task Submission is required for publication changes."))

    actor = actor or frappe.session.user
    _require_feedback_submission_context(outcome_id, submission_id)
    workspace_doc = _get_or_create_workspace_doc(outcome_id, submission_id)

    workspace_doc.feedback_visibility = _normalize_visibility_state(data.get("feedback_visibility"))
    workspace_doc.grade_visibility = _normalize_visibility_state(data.get("grade_visibility"))

    if workspace_doc.is_new():
        _save_workspace_doc(workspace_doc)
    else:
        workspace_doc.save(ignore_permissions=True)

    _log_publication_change(outcome_id, workspace_doc, actor=actor)
    return build_feedback_workspace_payload(outcome_id, submission_id) or {}


def normalize_feedback_anchor_payload(
    kind: str, page_number: int | str | None, payload: str | dict[str, Any] | None
) -> dict[str, Any]:
    resolved_kind = _normalize_anchor_kind(kind)
    resolved_page = _normalize_page_number(page_number)
    data = _coerce_json_dict(payload)

    if resolved_kind == "page":
        return {"kind": "page", "page": resolved_page}

    if resolved_kind == "point":
        point = data.get("point") if isinstance(data.get("point"), dict) else data
        x = _normalize_unit(point.get("x"))
        y = _normalize_unit(point.get("y"))
        return {"kind": "point", "page": resolved_page, "point": {"x": x, "y": y}}

    if resolved_kind == "rect":
        rect = data.get("rect") if isinstance(data.get("rect"), dict) else data
        x = _normalize_unit(rect.get("x"))
        y = _normalize_unit(rect.get("y"))
        width = _normalize_positive_unit(rect.get("width"))
        height = _normalize_positive_unit(rect.get("height"))
        if x + width > 1:
            width = max(0.0, 1.0 - x)
        if y + height > 1:
            height = max(0.0, 1.0 - y)
        return {
            "kind": "rect",
            "page": resolved_page,
            "rect": {"x": x, "y": y, "width": width, "height": height},
        }

    if resolved_kind == "text_quote":
        quote = _clean_text(data.get("quote"))
        if not quote:
            frappe.throw(_("Text-quote anchors require quoted text."))
        return {
            "kind": "text_quote",
            "page": resolved_page,
            "quote": quote,
            "rects": data.get("rects") or [],
            "selector": data.get("selector") or {},
        }

    strokes = data.get("strokes")
    if not isinstance(strokes, list) or not strokes:
        frappe.throw(_("Path anchors require at least one stroke."))
    return {"kind": "path", "page": resolved_page, "strokes": strokes}


def _load_feedback_item_rows(workspace_id: str) -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "Task Feedback Item",
        filters={
            "parent": workspace_id,
            "parenttype": "Task Feedback Workspace",
            "parentfield": "feedback_items",
        },
        fields=[
            "name",
            "anchor_kind",
            "page_number",
            "feedback_intent",
            "workflow_state",
            "body",
            "anchor_payload",
            "assessment_criteria",
            "author",
        ],
        order_by="idx asc",
        limit=0,
    )
    payload = []
    for row in rows:
        anchor = normalize_feedback_anchor_payload(
            row.get("anchor_kind"),
            row.get("page_number"),
            row.get("anchor_payload"),
        )
        payload.append(
            {
                "id": row.get("name"),
                "kind": anchor.get("kind"),
                "page": anchor.get("page"),
                "intent": _normalize_feedback_intent(row.get("feedback_intent")),
                "workflow_state": _normalize_workflow_state(row.get("workflow_state")),
                "comment": row.get("body") or "",
                "anchor": anchor,
                "assessment_criteria": _clean_text(row.get("assessment_criteria")),
                "author": _clean_text(row.get("author")),
            }
        )
    return payload


def _load_feedback_priority_rows(workspace_id: str) -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "Task Feedback Priority",
        filters={
            "parent": workspace_id,
            "parenttype": "Task Feedback Workspace",
            "parentfield": "priorities",
        },
        fields=["name", "title", "detail", "feedback_item_id", "assessment_criteria"],
        order_by="idx asc",
        limit=0,
    )
    return [
        {
            "id": row.get("name"),
            "title": row.get("title") or "",
            "detail": row.get("detail") or "",
            "feedback_item_id": _clean_text(row.get("feedback_item_id")),
            "assessment_criteria": _clean_text(row.get("assessment_criteria")),
        }
        for row in rows
    ]


def _get_or_create_workspace_doc(outcome_id: str, submission_id: str):
    existing_name = frappe.db.get_value(
        "Task Feedback Workspace",
        {"task_outcome": outcome_id, "task_submission": submission_id},
        "name",
    )
    if existing_name:
        return frappe.get_doc("Task Feedback Workspace", existing_name)

    submission = _require_feedback_submission_context(outcome_id, submission_id)
    outcome = _get_outcome_context(outcome_id)
    doc = frappe.new_doc("Task Feedback Workspace")
    doc.task_outcome = outcome_id
    doc.task_submission = submission_id
    doc.submission_version = submission.get("version")
    doc.feedback_visibility = "hidden"
    doc.grade_visibility = "hidden"
    for field in ("task_delivery", "task", "student", "student_group", "school", "course", "academic_year"):
        setattr(doc, field, outcome.get(field))
    return doc


def _save_workspace_doc(doc):
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)


def _log_publication_change(outcome_id: str, workspace_doc, *, actor: str):
    content = (
        "Feedback publication updated:\n"
        f"- feedback_visibility: {workspace_doc.feedback_visibility}\n"
        f"- grade_visibility: {workspace_doc.grade_visibility}\n"
        f"- actor: {actor}"
    )
    try:
        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Task Outcome",
                "reference_name": outcome_id,
                "content": content,
            }
        ).insert(ignore_permissions=True)
    except Exception:
        # Track-changes on the workspace still captures the change; comment logging is best-effort.
        return


def _normalize_feedback_item_record(raw_item: dict[str, Any], *, actor: str) -> dict[str, Any]:
    kind = _normalize_anchor_kind(raw_item.get("kind"))
    page = _normalize_page_number(raw_item.get("page"))
    anchor = normalize_feedback_anchor_payload(kind, page, raw_item.get("anchor"))
    return {
        "anchor_kind": anchor.get("kind"),
        "page_number": anchor.get("page"),
        "feedback_intent": _normalize_feedback_intent(raw_item.get("intent")),
        "workflow_state": _normalize_workflow_state(raw_item.get("workflow_state")),
        "body": _clean_text(raw_item.get("comment")),
        "anchor_payload": json.dumps(anchor, separators=(",", ":"), sort_keys=True),
        "assessment_criteria": _clean_text(raw_item.get("assessment_criteria")),
        "author": _clean_text(raw_item.get("author")) or actor,
    }


def _normalize_feedback_priority_record(raw_priority: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text(raw_priority.get("title"))
    if not title:
        frappe.throw(_("Pinned priorities require a title."))
    return {
        "title": title,
        "detail": _clean_text(raw_priority.get("detail")),
        "feedback_item_id": _clean_text(raw_priority.get("feedback_item_id")),
        "assessment_criteria": _clean_text(raw_priority.get("assessment_criteria")),
    }


def _normalize_anchor_kind(value: Any) -> str:
    resolved = str(value or "").strip().lower()
    if resolved not in FEEDBACK_ITEM_KINDS:
        frappe.throw(_("Unsupported feedback anchor kind."))
    return resolved


def _normalize_feedback_intent(value: Any) -> str:
    resolved = str(value or "issue").strip().lower()
    if resolved not in FEEDBACK_INTENT_OPTIONS:
        frappe.throw(_("Unsupported feedback intent."))
    return resolved


def _normalize_workflow_state(value: Any) -> str:
    resolved = str(value or "draft").strip().lower()
    if resolved not in FEEDBACK_WORKFLOW_STATES:
        frappe.throw(_("Unsupported feedback workflow state."))
    return resolved


def _normalize_visibility_state(value: Any) -> str:
    resolved = str(value or "hidden").strip().lower()
    if resolved not in PUBLICATION_VISIBILITY_STATES:
        frappe.throw(_("Unsupported publication visibility state."))
    return resolved


def _normalize_publication_audience(value: Any) -> str:
    resolved = str(value or "student").strip().lower()
    if resolved not in PUBLICATION_AUDIENCES:
        frappe.throw(_("Unsupported publication audience."))
    return resolved


def _normalize_page_number(value: Any) -> int:
    try:
        resolved = int(value or 0)
    except Exception:
        resolved = 0
    if resolved <= 0:
        frappe.throw(_("Feedback anchors require a positive page number."))
    return resolved


def _normalize_unit(value: Any) -> float:
    try:
        resolved = float(value)
    except Exception:
        frappe.throw(_("Feedback anchor coordinates must be numeric."))
    if resolved < 0 or resolved > 1:
        frappe.throw(_("Feedback anchor coordinates must stay between 0 and 1."))
    return round(resolved, 6)


def _normalize_positive_unit(value: Any) -> float:
    resolved = _normalize_unit(value)
    if resolved <= 0:
        frappe.throw(_("Feedback anchor dimensions must be greater than 0."))
    return resolved


def _coerce_json_dict(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            frappe.throw(_("Feedback anchor payload must be valid JSON."))
        if isinstance(parsed, dict):
            return parsed
    frappe.throw(_("Feedback anchor payload must be a dict."))


def _normalize_payload(payload: dict[str, Any] | str | None) -> dict[str, Any]:
    if payload is None:
        frappe.throw(_("Payload must be a dict."))
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("Payload must be a dict."))
    return payload


def _coerce_items(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        frappe.throw(_("Feedback items must be a list."))
    next_items: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            frappe.throw(_("Each feedback item must be a dict."))
        next_items.append(row)
    return next_items


def _coerce_priorities(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        frappe.throw(_("Pinned priorities must be a list."))
    next_rows: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            frappe.throw(_("Each pinned priority must be a dict."))
        next_rows.append(row)
    return next_rows


def _replace_child_rows_preserving_names(doc, fieldname: str, rows: list[dict[str, Any]], *, id_key: str = "id"):
    doc.set(fieldname, [])
    for row in rows:
        prepared = {key: value for key, value in row.items() if key != id_key}
        resolved_name = _clean_text(row.get(id_key))
        if resolved_name:
            prepared["name"] = resolved_name
        doc.append(fieldname, prepared)


def _resolve_publication_defaults(
    workspace_row: dict[str, Any] | None, legacy_release: dict[str, Any]
) -> tuple[str, str]:
    if workspace_row:
        return (
            _normalize_visibility_state(workspace_row.get("feedback_visibility")),
            _normalize_visibility_state(workspace_row.get("grade_visibility")),
        )
    if int(legacy_release.get("is_published") or 0):
        return ("student_and_guardian", "student_and_guardian")
    return ("hidden", "hidden")


def _get_legacy_release_state(outcome_id: str) -> dict[str, Any]:
    return frappe.db.get_value(
        "Task Outcome",
        outcome_id,
        ["name", "is_published", "published_on", "published_by"],
        as_dict=True,
    ) or {"name": outcome_id, "is_published": 0, "published_on": None, "published_by": None}


def _publication_payload_from_legacy(outcome: dict[str, Any]) -> dict[str, Any]:
    legacy_release = _get_legacy_release_state(outcome.get("name"))
    feedback_visibility, grade_visibility = _resolve_publication_defaults(None, legacy_release)
    return {
        "feedback_visibility": feedback_visibility,
        "grade_visibility": grade_visibility,
        "derived_from_legacy_outcome": True,
        "legacy_outcome_published": bool(int(legacy_release.get("is_published") or 0)),
        "legacy_published_on": legacy_release.get("published_on"),
        "legacy_published_by": legacy_release.get("published_by"),
    }


def _resolve_submission_context_for_release(outcome_id: str, submission_id: str | None = None) -> str | None:
    resolved_submission_id = _clean_text(submission_id)
    if resolved_submission_id:
        return resolved_submission_id

    latest_rows = frappe.get_all(
        "Task Submission",
        filters={"task_outcome": outcome_id},
        fields=["name"],
        order_by="version desc, modified desc",
        limit=1,
    )
    if latest_rows:
        return _clean_text(latest_rows[0].get("name"))
    return None


def _get_released_result_outcome_context(outcome_id: str) -> dict[str, Any]:
    fields = [
        "name",
        "task_delivery",
        "task",
        "student",
        "course",
        "official_score",
        "official_grade",
        "official_grade_value",
        "official_feedback",
        "is_published",
        "published_on",
        "published_by",
    ]
    row = frappe.db.get_value("Task Outcome", outcome_id, fields, as_dict=True)
    if not row:
        frappe.throw(_("Task Outcome not found."))
    return row


def _get_outcome_context(outcome_id: str) -> dict[str, Any]:
    fields = ["task_delivery", "task", "student", "student_group", "school", "course", "academic_year"]
    row = frappe.db.get_value("Task Outcome", outcome_id, fields, as_dict=True)
    if not row:
        frappe.throw(_("Task Outcome not found."))
    return row


def _get_release_context(outcome_id: str) -> dict[str, Any]:
    outcome = _get_released_result_outcome_context(outcome_id)
    task_delivery = _clean_text(outcome.get("task_delivery"))
    delivery_row = (
        frappe.db.get_value(
            "Task Delivery",
            task_delivery,
            ["name", "title", "task_type"],
            as_dict=True,
        )
        if task_delivery
        else None
    ) or {}
    course = _clean_text(outcome.get("course"))
    course_name = _clean_text(frappe.db.get_value("Course", course, "course_name")) if course else None
    return {
        "task_delivery": task_delivery,
        "task": _clean_text(outcome.get("task")),
        "title": _clean_text(delivery_row.get("title")) or task_delivery or outcome_id,
        "task_type": _clean_text(delivery_row.get("task_type")),
        "course": course,
        "course_name": course_name,
        "student": _clean_text(outcome.get("student")),
    }


def _require_feedback_submission_context(outcome_id: str, submission_id: str) -> dict[str, Any]:
    fields = ["name", "task_outcome", "version"]
    row = frappe.db.get_value("Task Submission", submission_id, fields, as_dict=True)
    if not row:
        frappe.throw(_("Task Submission not found."))
    if row.get("task_outcome") != outcome_id:
        frappe.throw(_("Task Submission does not belong to the selected Task Outcome."))
    return row


def _build_released_rubric_snapshot(
    outcome_id: str,
    feedback_items: list[dict[str, Any]],
    *,
    grade_visible: bool,
    feedback_visible: bool,
) -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "Task Outcome Criterion",
        filters={
            "parent": outcome_id,
            "parenttype": "Task Outcome",
            "parentfield": "criteria",
        },
        fields=["assessment_criteria", "level", "level_points", "feedback"],
        order_by="idx asc",
        limit=0,
    )
    if not rows:
        return []
    criteria_ids = [
        _clean_text(row.get("assessment_criteria")) for row in rows if _clean_text(row.get("assessment_criteria"))
    ]
    criteria_meta = frappe.get_all(
        "Assessment Criteria",
        filters={"name": ["in", criteria_ids]} if criteria_ids else {"name": ["in", [""]]},
        fields=["name", "assessment_criteria"],
        limit=0,
    )
    name_map = {
        _clean_text(row.get("name")): _clean_text(row.get("assessment_criteria"))
        for row in criteria_meta
        if _clean_text(row.get("name"))
    }
    linked_item_ids_by_criteria: dict[str, list[str]] = {}
    for item in feedback_items:
        criteria_id = _clean_text(item.get("assessment_criteria"))
        item_id = _clean_text(item.get("id"))
        if not criteria_id or not item_id:
            continue
        linked_item_ids_by_criteria.setdefault(criteria_id, []).append(item_id)
    return [
        {
            "assessment_criteria": _clean_text(row.get("assessment_criteria")),
            "criteria_name": name_map.get(_clean_text(row.get("assessment_criteria")))
            or _clean_text(row.get("assessment_criteria")),
            "level": _clean_text(row.get("level")) if grade_visible else None,
            "points": row.get("level_points") if grade_visible else None,
            "feedback": _clean_text(row.get("feedback")) if feedback_visible else None,
            "linked_feedback_item_ids": linked_item_ids_by_criteria.get(
                _clean_text(row.get("assessment_criteria")) or "",
                [],
            ),
        }
        for row in rows
    ]


def _clean_text(value: Any) -> str | None:
    resolved = str(value or "").strip()
    return resolved or None


def _feedback_workspace_reads_available() -> bool:
    return _doctype_read_columns_available("Task Feedback Workspace", WORKSPACE_READ_COLUMNS)


def _feedback_item_reads_available() -> bool:
    return _doctype_read_columns_available("Task Feedback Item", FEEDBACK_ITEM_READ_COLUMNS)


def _feedback_priority_reads_available() -> bool:
    return _doctype_read_columns_available("Task Feedback Priority", FEEDBACK_PRIORITY_READ_COLUMNS)


def _feedback_thread_reads_available() -> bool:
    return _doctype_read_columns_available("Task Feedback Thread", FEEDBACK_THREAD_READ_COLUMNS) and (
        _doctype_read_columns_available("Task Feedback Thread Message", FEEDBACK_THREAD_MESSAGE_READ_COLUMNS)
    )


def _doctype_read_columns_available(doctype: str, fieldnames: tuple[str, ...]) -> bool:
    db = getattr(frappe, "db", None)
    table_exists = getattr(db, "table_exists", None)
    if callable(table_exists) and not table_exists(doctype):
        return False

    has_column = getattr(db, "has_column", None)
    if not callable(has_column):
        return True
    return all(has_column(doctype, fieldname) for fieldname in fieldnames)
