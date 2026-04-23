# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from ifitwala_ed.api import courses as courses_api
from ifitwala_ed.api import guardian_home
from ifitwala_ed.api import task_submission as task_submission_api
from ifitwala_ed.assessment import (
    task_feedback_artifact_service,
    task_feedback_service,
    task_feedback_thread_service,
)


@frappe.whitelist()
def get_student_released_feedback_detail(outcome_id: str) -> dict[str, Any]:
    _require_authenticated()
    _require_student_outcome_access(outcome_id)
    detail = task_feedback_service.build_released_feedback_detail_payload(
        outcome_id,
        audience="student",
    )
    detail["document"] = _build_student_document_payload(detail.get("task_submission"))
    return detail


@frappe.whitelist()
def get_guardian_released_feedback_detail(outcome_id: str) -> dict[str, Any]:
    _require_authenticated()
    _require_guardian_outcome_access(outcome_id)
    detail = task_feedback_service.build_released_feedback_detail_payload(
        outcome_id,
        audience="guardian",
    )
    detail["document"] = None
    return detail


@frappe.whitelist()
def save_student_feedback_reply(payload=None, **kwargs) -> dict[str, Any]:
    _require_authenticated()
    data = _normalize_payload(payload, kwargs)
    outcome_id = _clean_text(data.get("outcome_id") or data.get("task_outcome"))
    _require_student_outcome_access(outcome_id)
    detail = task_feedback_service.build_released_feedback_detail_payload(
        outcome_id,
        audience="student",
    )
    if not detail.get("allowed_actions", {}).get("can_reply"):
        frappe.throw(_("Replies are not available for this feedback release."), frappe.PermissionError)
    thread = task_feedback_thread_service.save_student_reply(data, actor=frappe.session.user)
    return {"thread": thread}


@frappe.whitelist()
def save_student_feedback_thread_state(payload=None, **kwargs) -> dict[str, Any]:
    _require_authenticated()
    data = _normalize_payload(payload, kwargs)
    outcome_id = _clean_text(data.get("outcome_id") or data.get("task_outcome"))
    _require_student_outcome_access(outcome_id)
    detail = task_feedback_service.build_released_feedback_detail_payload(
        outcome_id,
        audience="student",
    )
    if not detail.get("allowed_actions", {}).get("can_set_learner_state"):
        frappe.throw(_("Learner actions are not available for this feedback release."), frappe.PermissionError)
    thread = task_feedback_thread_service.save_student_learner_state(data, actor=frappe.session.user)
    return {"thread": thread}


@frappe.whitelist()
def export_student_released_feedback_pdf(outcome_id: str) -> dict[str, Any]:
    _require_authenticated()
    _require_student_outcome_access(outcome_id)
    artifact = task_feedback_artifact_service.export_released_feedback_pdf(
        outcome_id,
        audience="student",
    )
    return {"artifact": artifact}


def _build_student_document_payload(submission_id: str | None) -> dict[str, Any] | None:
    resolved_submission_id = _clean_text(submission_id)
    if not resolved_submission_id:
        return None
    submission_row = frappe.db.get_value(
        "Task Submission",
        resolved_submission_id,
        [
            "name",
            "version",
            "submitted_on",
            "submitted_by",
            "submission_origin",
            "is_stub",
            "evidence_note",
            "is_cloned",
            "cloned_from",
            "text_content",
            "link_url",
        ],
        as_dict=True,
    )
    if not submission_row:
        return None
    evidence = task_submission_api.serialize_task_submission_evidence(submission_row, is_latest_version=None)
    primary_attachment = _select_primary_document_attachment(evidence)
    return {
        "submission": evidence,
        "primary_attachment": primary_attachment,
    }


def _select_primary_document_attachment(submission: dict[str, Any]) -> dict[str, Any] | None:
    readiness = submission.get("annotation_readiness") or {}
    target_row_name = _clean_text(readiness.get("attachment_row_name"))
    attachments = submission.get("attachments") or []
    if target_row_name:
        for row in attachments:
            if _clean_text(row.get("row_name")) == target_row_name:
                return {
                    "row_name": target_row_name,
                    "attachment_preview": row.get("attachment_preview"),
                    "preview_url": row.get("preview_url"),
                    "open_url": row.get("open_url"),
                }
    for row in attachments:
        attachment_preview = row.get("attachment_preview") or {}
        extension = _clean_text(row.get("extension")) or _clean_text(attachment_preview.get("extension"))
        mime_type = _clean_text(row.get("mime_type")) or _clean_text(attachment_preview.get("mime_type"))
        if mime_type == "application/pdf" or extension == "pdf":
            return {
                "row_name": _clean_text(row.get("row_name")),
                "attachment_preview": row.get("attachment_preview"),
                "preview_url": row.get("preview_url"),
                "open_url": row.get("open_url"),
            }
    return None


def _require_student_outcome_access(outcome_id: str) -> str:
    resolved_outcome_id = _clean_text(outcome_id)
    if not resolved_outcome_id:
        frappe.throw(_("Task Outcome is required."), frappe.ValidationError)
    student_name = courses_api._require_student_name_for_session_user()
    outcome_student = _clean_text(frappe.db.get_value("Task Outcome", resolved_outcome_id, "student"))
    if outcome_student != student_name:
        frappe.throw(_("You do not have access to this released feedback."), frappe.PermissionError)
    return student_name


def _require_guardian_outcome_access(outcome_id: str) -> str:
    resolved_outcome_id = _clean_text(outcome_id)
    if not resolved_outcome_id:
        frappe.throw(_("Task Outcome is required."), frappe.ValidationError)
    _guardian_context, children = guardian_home._resolve_guardian_scope(frappe.session.user)
    allowed_students = {row.get("student") for row in children if row.get("student")}
    outcome_student = _clean_text(frappe.db.get_value("Task Outcome", resolved_outcome_id, "student"))
    if outcome_student not in allowed_students:
        frappe.throw(_("You do not have access to this released feedback."), frappe.PermissionError)
    return outcome_student or ""


def _normalize_payload(payload, kwargs) -> dict[str, Any]:
    data = payload if payload is not None else kwargs
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        frappe.throw(_("Payload must be a dict."))
    return data


def _require_authenticated():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Not permitted."), frappe.PermissionError)


def _clean_text(value: Any) -> str | None:
    resolved = str(value or "").strip()
    return resolved or None
