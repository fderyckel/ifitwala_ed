from __future__ import annotations

import re
from datetime import datetime
from html import escape
from types import SimpleNamespace
from typing import Any

import frappe
from frappe import _

from ifitwala_ed.api.attachment_previews import (
    build_attachment_preview_item,
    extract_file_extension,
    guess_mime_type,
)
from ifitwala_ed.api.file_access import (
    resolve_academic_file_open_url,
    resolve_academic_file_preview_url,
)
from ifitwala_ed.assessment import task_feedback_service
from ifitwala_ed.integrations.drive import tasks as drive_tasks
from ifitwala_ed.integrations.drive.authority import get_current_drive_file_for_slot
from ifitwala_ed.integrations.drive.content_uploads import upload_content_via_drive

SUPPORTED_EXPORT_AUDIENCES = ("student",)


def export_released_feedback_pdf(
    outcome_id: str,
    *,
    audience: str = "student",
    submission_id: str | None = None,
) -> dict[str, Any]:
    resolved_outcome_id = _clean_text(outcome_id)
    if not resolved_outcome_id:
        frappe.throw(_("Task Outcome is required for feedback export."))

    resolved_audience = _normalize_export_audience(audience)
    detail = task_feedback_service.build_released_feedback_detail_payload(
        resolved_outcome_id,
        audience=resolved_audience,
        submission_id=submission_id,
    )
    if not detail.get("feedback_visible"):
        frappe.throw(_("Released feedback is not available for PDF export."), frappe.PermissionError)

    submission_id = _clean_text(detail.get("task_submission"))
    if not submission_id:
        frappe.throw(_("Released feedback export requires a bound Task Submission version."))

    current_artifact = get_current_released_feedback_pdf_artifact(
        resolved_outcome_id,
        audience=resolved_audience,
        submission_id=submission_id,
        detail=detail,
    )
    if current_artifact:
        return current_artifact

    html = _render_released_feedback_html(detail)

    from frappe.utils.pdf import get_pdf

    pdf_content = get_pdf(html)
    file_name = _build_export_filename(detail)
    _session_response, finalize_response, file_doc = upload_content_via_drive(
        workflow_id="task.feedback_export",
        workflow_payload={
            "task_submission": submission_id,
            "outcome_id": resolved_outcome_id,
            "audience": resolved_audience,
            "artifact_kind": "released_feedback_pdf",
        },
        file_name=file_name,
        content=pdf_content,
        mime_type_hint="application/pdf",
    )
    return _build_artifact_payload(
        submission_id=submission_id,
        submission_version=((detail.get("feedback") or {}).get("submission_version")),
        file_id=getattr(file_doc, "name", None),
        file_name=getattr(file_doc, "file_name", None),
        file_url=getattr(file_doc, "file_url", None),
        preview_status=(finalize_response or {}).get("preview_status"),
    )


def get_current_released_feedback_pdf_artifact(
    outcome_id: str,
    *,
    audience: str = "student",
    submission_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    resolved_outcome_id = _clean_text(outcome_id)
    if not resolved_outcome_id:
        frappe.throw(_("Task Outcome is required for feedback artifact lookup."))

    resolved_audience = _normalize_export_audience(audience)
    released = detail or task_feedback_service.build_released_result_payload(
        resolved_outcome_id,
        audience=resolved_audience,
        submission_id=submission_id,
    )
    if not released.get("feedback_visible"):
        return None

    resolved_submission_id = _clean_text(released.get("task_submission"))
    if not resolved_submission_id:
        return None

    submission_row = frappe.db.get_value(
        "Task Submission",
        resolved_submission_id,
        ["name", "student", "school"],
        as_dict=True,
    )
    if not submission_row or not _clean_text(submission_row.get("student")):
        return None

    drive_file = get_current_drive_file_for_slot(
        primary_subject_type="Student",
        primary_subject_id=_clean_text(submission_row.get("student")),
        slot=_feedback_export_slot(resolved_submission_id, submission_row, resolved_audience),
        school=_clean_text(submission_row.get("school")),
        attached_doctype="Task Submission",
        attached_name=resolved_submission_id,
        fields=("file", "preview_status", "modified", "creation"),
    )
    if not drive_file or not _clean_text(drive_file.get("file")):
        return None
    if not _artifact_is_fresh(drive_file, released, outcome_id=resolved_outcome_id):
        return None

    file_row = frappe.db.get_value(
        "File",
        _clean_text(drive_file.get("file")),
        ["name", "file_name", "file_url"],
        as_dict=True,
    )
    if not file_row:
        return None

    return _build_artifact_payload(
        submission_id=resolved_submission_id,
        submission_version=((released.get("feedback") or {}).get("submission_version")),
        file_id=file_row.get("name"),
        file_name=file_row.get("file_name"),
        file_url=file_row.get("file_url"),
        preview_status=drive_file.get("preview_status"),
    )


def _build_artifact_payload(
    *,
    submission_id: str,
    submission_version: Any = None,
    file_id: Any = None,
    file_name: Any = None,
    file_url: Any = None,
    preview_status: Any = None,
) -> dict[str, Any]:
    file_id = _clean_text(file_id)
    file_name = _clean_text(file_name)
    file_url = _clean_text(file_url)
    preview_url = resolve_academic_file_preview_url(
        file_name=file_id,
        file_url=file_url,
        context_doctype="Task Submission",
        context_name=submission_id,
    )
    open_url = resolve_academic_file_open_url(
        file_name=file_id,
        file_url=file_url,
        context_doctype="Task Submission",
        context_name=submission_id,
    )
    mime_type = "application/pdf"
    extension = extract_file_extension(file_name=file_name, file_url=file_url) or "pdf"
    return {
        "file_id": file_id,
        "file_name": file_name,
        "task_submission": submission_id,
        "submission_version": submission_version,
        "preview_status": _clean_text(preview_status),
        "open_url": open_url,
        "preview_url": preview_url,
        "attachment_preview": build_attachment_preview_item(
            item_id=file_id,
            owner_doctype="Task Submission",
            owner_name=submission_id,
            file_id=file_id,
            display_name=file_name,
            mime_type=mime_type or guess_mime_type(file_name=file_name, file_url=file_url),
            extension=extension,
            preview_status=preview_status,
            preview_url=preview_url,
            open_url=open_url,
        ),
    }


def _feedback_export_slot(submission_id: str, submission_row: dict[str, Any], audience: str) -> str:
    authoritative = drive_tasks.build_task_feedback_export_upload_contract(
        SimpleNamespace(
            name=submission_id,
            student=_clean_text(submission_row.get("student")),
            school=_clean_text(submission_row.get("school")),
        ),
        audience=audience,
    )
    return _clean_text(authoritative.get("slot")) or ""


def _artifact_is_fresh(drive_file: dict[str, Any], released: dict[str, Any], *, outcome_id: str) -> bool:
    artifact_modified = _coerce_datetime(drive_file.get("modified")) or _coerce_datetime(drive_file.get("creation"))
    if not artifact_modified:
        return False

    source_timestamps = [
        _coerce_datetime((released.get("feedback") or {}).get("modified")),
        _coerce_datetime((released.get("publication") or {}).get("legacy_published_on")),
        _coerce_datetime(frappe.db.get_value("Task Outcome", outcome_id, "modified")),
    ]
    relevant_sources = [value for value in source_timestamps if value is not None]
    if not relevant_sources:
        return True
    return artifact_modified >= max(relevant_sources)


def _coerce_datetime(value: Any) -> datetime | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    try:
        from frappe.utils import get_datetime

        coerced = get_datetime(cleaned)
        if isinstance(coerced, datetime):
            return coerced
    except Exception:
        pass
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        return None


def _build_export_filename(detail: dict[str, Any]) -> str:
    student = _clean_text((detail.get("context") or {}).get("student")) or "student"
    title = _clean_text((detail.get("context") or {}).get("title")) or "released-feedback"
    version = (detail.get("feedback") or {}).get("submission_version")
    version_label = f"v{int(version)}" if isinstance(version, int) or str(version or "").isdigit() else "v1"
    return f"released-feedback-{_slugify(student)}-{_slugify(title)}-{version_label}.pdf"


def _render_released_feedback_html(detail: dict[str, Any]) -> str:
    feedback = dict(detail.get("feedback") or {})
    official = dict(detail.get("official") or {})
    context = dict(detail.get("context") or {})
    summary = dict(feedback.get("summary") or {})
    priorities = list(feedback.get("priorities") or [])
    items = list(feedback.get("items") or [])
    rubric_snapshot = list(feedback.get("rubric_snapshot") or [])
    student = _clean_text(context.get("student"))
    student_name = _clean_text(frappe.db.get_value("Student", student, "student_name")) if student else None

    summary_cards = [
        ("Overall Summary", summary.get("overall")),
        ("Strengths", summary.get("strengths")),
        ("Improvements", summary.get("improvements")),
        ("Next Steps", summary.get("next_steps")),
    ]

    summary_html = "".join(
        _render_named_block(label, body) for label, body in summary_cards if _clean_text(body)
    ) or _render_named_block("Summary", _("No released summary was available."))

    priorities_html = "".join(
        f"""
        <li class="priority-item">
            <div class="priority-title">{_safe_text(priority.get("title"))}</div>
            {_optional_block("priority-detail", priority.get("detail"))}
        </li>
        """
        for priority in priorities
    )

    rubric_html = "".join(
        f"""
        <tr>
            <td>{_safe_text(row.get("criteria_name"))}</td>
            <td>{_safe_text(row.get("level"))}</td>
            <td>{_safe_text(row.get("points"))}</td>
            <td>{_safe_text(row.get("feedback"))}</td>
        </tr>
        """
        for row in rubric_snapshot
    )

    items_html = (
        "".join(
            f"""
        <article class="feedback-item">
            <div class="feedback-item-meta">
                <span class="chip">{_safe_text(_intent_label(row.get("intent")))}</span>
                <span class="chip">Page {_safe_text(row.get("page"))}</span>
            </div>
            <p class="feedback-item-body">{_safe_text(row.get("comment"))}</p>
        </article>
        """
            for row in items
        )
        or '<p class="empty-copy">No released anchored comments were available.</p>'
    )

    official_html = ""
    if detail.get("grade_visible") and any(
        official.get(key) not in (None, "") for key in ("score", "grade", "feedback")
    ):
        official_html = f"""
        <section class="section">
            <h2>Official Result</h2>
            <div class="meta-grid">
                <div><span class="meta-label">Score</span><span>{_safe_text(official.get("score"))}</span></div>
                <div><span class="meta-label">Grade</span><span>{_safe_text(official.get("grade"))}</span></div>
            </div>
            {_optional_block("official-feedback", official.get("feedback"))}
        </section>
        """

    priorities_section = ""
    if priorities_html:
        priorities_section = f"""
        <section class="section">
            <h2>Pinned Priorities</h2>
            <ul class="priority-list">{priorities_html}</ul>
        </section>
        """

    rubric_section = ""
    if rubric_html:
        rubric_section = f"""
        <section class="section">
            <h2>Rubric Snapshot</h2>
            <table class="rubric-table">
                <thead>
                    <tr>
                        <th>Criterion</th>
                        <th>Level</th>
                        <th>Points</th>
                        <th>Feedback</th>
                    </tr>
                </thead>
                <tbody>{rubric_html}</tbody>
            </table>
        </section>
        """

    return f"""
    <html>
        <head>
            <meta charset="utf-8" />
            <style>
                body {{
                    font-family: Inter, Helvetica, Arial, sans-serif;
                    color: #182027;
                    margin: 28px;
                    line-height: 1.45;
                }}
                h1, h2, h3, p {{ margin: 0; }}
                h1 {{
                    font-size: 22px;
                    margin-bottom: 8px;
                }}
                h2 {{
                    font-size: 14px;
                    letter-spacing: 0.04em;
                    text-transform: uppercase;
                    color: #4b5b67;
                    margin-bottom: 12px;
                }}
                .hero {{
                    padding: 18px 20px;
                    border: 1px solid #d9e1e7;
                    border-radius: 18px;
                    background: #f8fafc;
                    margin-bottom: 20px;
                }}
                .hero-copy {{
                    color: #51606c;
                    margin-top: 10px;
                }}
                .meta-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 12px;
                    margin-top: 14px;
                }}
                .meta-grid div {{
                    padding: 12px 14px;
                    border-radius: 14px;
                    border: 1px solid #d9e1e7;
                    background: #ffffff;
                }}
                .meta-label {{
                    display: block;
                    color: #61717d;
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                    margin-bottom: 6px;
                }}
                .section {{
                    margin-top: 20px;
                    padding: 18px 20px;
                    border: 1px solid #d9e1e7;
                    border-radius: 18px;
                    background: #ffffff;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 12px;
                }}
                .summary-card {{
                    border: 1px solid #d9e1e7;
                    border-radius: 14px;
                    padding: 14px;
                    background: #f8fafc;
                }}
                .summary-label {{
                    display: block;
                    color: #61717d;
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                    margin-bottom: 8px;
                }}
                .summary-body, .official-feedback, .priority-detail, .feedback-item-body, .empty-copy {{
                    color: #33424d;
                    font-size: 13px;
                    white-space: pre-wrap;
                }}
                .priority-list {{
                    list-style: none;
                    margin: 0;
                    padding: 0;
                    display: grid;
                    gap: 12px;
                }}
                .priority-item {{
                    border: 1px solid #d9e1e7;
                    border-radius: 14px;
                    padding: 14px;
                    background: #f8fafc;
                }}
                .priority-title {{
                    font-weight: 600;
                    margin-bottom: 8px;
                }}
                .rubric-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 12px;
                }}
                .rubric-table th,
                .rubric-table td {{
                    border-top: 1px solid #d9e1e7;
                    padding: 10px 8px;
                    vertical-align: top;
                    text-align: left;
                }}
                .rubric-table th {{
                    color: #61717d;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    font-size: 10px;
                    border-top: 0;
                }}
                .feedback-item {{
                    border: 1px solid #d9e1e7;
                    border-radius: 14px;
                    padding: 14px;
                    background: #f8fafc;
                    margin-top: 12px;
                }}
                .feedback-item-meta {{
                    margin-bottom: 10px;
                }}
                .chip {{
                    display: inline-block;
                    border-radius: 999px;
                    border: 1px solid #d9e1e7;
                    padding: 4px 8px;
                    margin-right: 6px;
                    font-size: 10px;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                    color: #52616c;
                    background: #ffffff;
                }}
            </style>
        </head>
        <body>
            <section class="hero">
                <p class="meta-label">Released Feedback</p>
                <h1>{_safe_text(context.get("title"))}</h1>
                <p class="hero-copy">{_safe_text(student_name or student or _("Student"))}</p>
                <div class="meta-grid">
                    <div>
                        <span class="meta-label">Course</span>
                        <span>{_safe_text(context.get("course_name") or context.get("course"))}</span>
                    </div>
                    <div>
                        <span class="meta-label">Submission Version</span>
                        <span>{_safe_text(feedback.get("submission_version"))}</span>
                    </div>
                    <div>
                        <span class="meta-label">Audience</span>
                        <span>{_safe_text(_normalize_export_audience("student").replace("_", " ").title())}</span>
                    </div>
                </div>
            </section>
            {official_html}
            <section class="section">
                <h2>Summary</h2>
                <div class="summary-grid">{summary_html}</div>
            </section>
            {priorities_section}
            {rubric_section}
            <section class="section">
                <h2>Feedback Notes</h2>
                {items_html}
            </section>
        </body>
    </html>
    """


def _render_named_block(label: str, body: Any) -> str:
    return f"""
    <article class="summary-card">
        <span class="summary-label">{_safe_text(label)}</span>
        <p class="summary-body">{_safe_text(body)}</p>
    </article>
    """


def _optional_block(css_class: str, body: Any) -> str:
    resolved = _clean_text(body)
    if not resolved:
        return ""
    return f'<p class="{css_class}">{_safe_text(resolved)}</p>'


def _intent_label(intent: Any) -> str:
    resolved = _clean_text(intent)
    if resolved == "next_step":
        return _("Next Step")
    if resolved == "rubric_evidence":
        return _("Rubric Evidence")
    return (resolved or _("Feedback")).replace("_", " ").title()


def _safe_text(value: Any) -> str:
    resolved = _clean_text(value) or "—"
    return escape(resolved).replace("\n", "<br />")


def _normalize_export_audience(value: Any) -> str:
    resolved = _clean_text(value) or "student"
    normalized = resolved.lower()
    if normalized not in SUPPORTED_EXPORT_AUDIENCES:
        frappe.throw(_("Unsupported released feedback export audience."))
    return normalized


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _slugify(value: Any) -> str:
    resolved = (_clean_text(value) or "item").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", resolved).strip("-")
    return slug or "item"
