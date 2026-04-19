# Copyright (c) 2026
# For license information, please see license.txt

from __future__ import annotations

import importlib
from typing import Any

import frappe
from frappe import _

from ifitwala_ed.api.attachment_previews import (
    build_attachment_preview_item,
    extract_file_extension,
    guess_mime_type,
)
from ifitwala_ed.api.file_access import resolve_academic_file_open_url, resolve_academic_file_preview_url
from ifitwala_ed.assessment import task_submission_service


def _frappe_module():
    return importlib.import_module("frappe")


def _translate_literal(message: str) -> str:
    current_frappe = _frappe_module()
    translator = getattr(current_frappe, "_", None)
    if callable(translator):
        return translator(message)
    return message


@frappe.whitelist()
def create_or_resubmit(payload=None, **kwargs):
    _require_authenticated()
    data = _normalize_payload(payload, kwargs)
    uploaded_files = _extract_uploaded_files()
    result = task_submission_service.create_student_submission(
        data,
        user=frappe.session.user,
        uploaded_files=uploaded_files,
    )
    return result


@frappe.whitelist()
def get_latest_submission(outcome_id=None):
    _require_authenticated()
    _require(outcome_id, "Task Outcome")

    rows = frappe.get_all(
        "Task Submission",
        filters={"task_outcome": outcome_id},
        fields=[
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
        order_by="version desc",
        limit=1,
    )
    if not rows:
        return None

    return serialize_task_submission_evidence(rows[0], is_latest_version=True)


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_flag(value) -> bool:
    try:
        return bool(int(value or 0))
    except Exception:
        return False


def _coerce_version(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        out = int(value)
    except Exception:
        frappe.throw(_("Version must be an integer."), frappe.ValidationError)
    if out < 1:
        frappe.throw(_("Version must be greater than zero."), frappe.ValidationError)
    return out


def select_task_submission_row(
    submission_rows: list[dict[str, Any]],
    *,
    submission_id: str | None = None,
    version: int | str | None = None,
) -> dict[str, Any] | None:
    if not submission_rows:
        return None

    resolved_submission_id = _clean_text(submission_id)
    resolved_version = _coerce_version(version)

    selected = None
    if resolved_submission_id:
        for row in submission_rows:
            if _clean_text(row.get("name")) == resolved_submission_id:
                selected = row
                break
        if not selected:
            frappe.throw(_("Task Submission version was not found for this outcome."), frappe.DoesNotExistError)
    elif resolved_version is not None:
        for row in submission_rows:
            if (row.get("version") or 0) == resolved_version:
                selected = row
                break
        if not selected:
            frappe.throw(_("Task Submission version was not found for this outcome."), frappe.DoesNotExistError)
    else:
        selected = submission_rows[0]

    if resolved_submission_id and resolved_version is not None and (selected.get("version") or 0) != resolved_version:
        frappe.throw(_("Submission ID and version do not match."), frappe.ValidationError)

    return selected


def build_task_submission_version_summary(
    submission_row: dict[str, Any],
    *,
    is_selected: bool = False,
) -> dict[str, Any]:
    return {
        "submission_id": submission_row.get("name"),
        "version": submission_row.get("version"),
        "submitted_on": submission_row.get("submitted_on"),
        "origin": submission_row.get("submission_origin"),
        "is_stub": _bool_flag(submission_row.get("is_stub")),
        "is_selected": bool(is_selected),
    }


def _load_submission_file_name_map(submission_id: str) -> dict[str, str]:
    resolved_submission_id = _clean_text(submission_id)
    if not resolved_submission_id:
        return {}

    current_frappe = _frappe_module()
    file_rows = current_frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Task Submission",
            "attached_to_name": resolved_submission_id,
        },
        fields=["name", "file_url", "creation"],
        order_by="creation desc",
        limit=0,
    )
    file_name_by_url: dict[str, str] = {}
    for row in file_rows:
        raw_url = _clean_text(row.get("file_url"))
        file_name = _clean_text(row.get("name"))
        if raw_url and file_name and raw_url not in file_name_by_url:
            file_name_by_url[raw_url] = file_name
    return file_name_by_url


def _load_submission_drive_file_meta_map(file_ids: list[str]) -> dict[str, dict[str, str | None]]:
    resolved_file_ids = [file_id for file_id in dict.fromkeys(file_ids) if _clean_text(file_id)]
    if not resolved_file_ids:
        return {}

    current_frappe = _frappe_module()
    try:
        drive_rows = current_frappe.get_all(
            "Drive File",
            filters={"file": ["in", resolved_file_ids]},
            fields=["file", "preview_status", "current_version"],
            limit=0,
        )
    except Exception:
        return {}

    current_version_ids = [
        current_version
        for current_version in (_clean_text(row.get("current_version")) for row in (drive_rows or []))
        if current_version
    ]
    mime_type_by_version: dict[str, str | None] = {}
    if current_version_ids:
        try:
            version_rows = current_frappe.get_all(
                "Drive File Version",
                filters={"name": ["in", current_version_ids]},
                fields=["name", "mime_type"],
                limit=0,
            )
        except Exception:
            version_rows = []
        mime_type_by_version = {
            _clean_text(row.get("name")): _clean_text(row.get("mime_type"))
            for row in version_rows
            if _clean_text(row.get("name"))
        }

    return {
        _clean_text(row.get("file")): {
            "preview_status": _clean_text(row.get("preview_status")),
            "mime_type": mime_type_by_version.get(_clean_text(row.get("current_version"))),
        }
        for row in drive_rows
        if _clean_text(row.get("file"))
    }


def _serialize_task_submission_attachment_row(
    attachment_row: dict[str, Any],
    *,
    submission_id: str,
    file_name_by_url: dict[str, str],
    drive_file_meta_by_file: dict[str, dict[str, str | None]],
    is_latest_version: bool | None = None,
    version_label: str | None = None,
) -> dict[str, Any]:
    file_url = _clean_text(attachment_row.get("file"))
    external_url = _clean_text(attachment_row.get("external_url"))
    description = _clean_text(attachment_row.get("description"))
    file_name = _clean_text(attachment_row.get("file_name"))
    file_size = attachment_row.get("file_size")
    row_name = _clean_text(attachment_row.get("name"))

    if file_url:
        resolved_file_id = file_name_by_url.get(file_url)
        drive_file_meta = drive_file_meta_by_file.get(resolved_file_id) or {}
        mime_type = _clean_text(drive_file_meta.get("mime_type")) or guess_mime_type(
            file_name=file_name,
            file_url=file_url,
        )
        extension = extract_file_extension(file_name=file_name, file_url=file_url)
        open_url = resolve_academic_file_open_url(
            file_name=resolved_file_id,
            file_url=file_url,
            context_doctype="Task Submission",
            context_name=submission_id,
        )
        preview_url = resolve_academic_file_preview_url(
            file_name=resolved_file_id,
            file_url=file_url,
            context_doctype="Task Submission",
            context_name=submission_id,
        )
        attachment_preview = build_attachment_preview_item(
            item_id=row_name or resolved_file_id or file_name,
            owner_doctype="Task Submission",
            owner_name=submission_id,
            file_id=resolved_file_id,
            display_name=file_name or resolved_file_id,
            description=description,
            mime_type=mime_type,
            extension=extension,
            size_bytes=file_size,
            preview_status=_clean_text(drive_file_meta.get("preview_status")),
            preview_url=preview_url,
            open_url=open_url,
            download_url=open_url,
            is_latest_version=is_latest_version,
            version_label=version_label,
        )
        return {
            "row_name": row_name,
            "kind": "file",
            "file": open_url,
            "file_name": file_name or resolved_file_id,
            "file_size": file_size,
            "description": description,
            "public": _bool_flag(attachment_row.get("public")),
            "preview_status": _clean_text(drive_file_meta.get("preview_status")),
            "preview_url": preview_url,
            "open_url": open_url,
            "external_url": None,
            "mime_type": mime_type,
            "extension": extension,
            "attachment_preview": attachment_preview,
        }
    attachment_preview = build_attachment_preview_item(
        item_id=row_name or external_url or file_name,
        owner_doctype="Task Submission",
        owner_name=submission_id,
        link_url=external_url,
        display_name=file_name or description or external_url,
        description=description,
        open_url=external_url,
        is_latest_version=is_latest_version,
        version_label=version_label,
    )
    return {
        "row_name": row_name,
        "kind": "link" if external_url else "other",
        "file": None,
        "file_name": file_name,
        "file_size": file_size,
        "description": description,
        "public": _bool_flag(attachment_row.get("public")),
        "preview_status": None,
        "preview_url": None,
        "open_url": external_url,
        "external_url": external_url,
        "mime_type": None,
        "extension": None,
        "attachment_preview": attachment_preview,
    }


def _load_task_submission_attachment_rows(
    submission_id: str,
    *,
    is_latest_version: bool | None = None,
    version_label: str | None = None,
) -> list[dict[str, Any]]:
    resolved_submission_id = _clean_text(submission_id)
    if not resolved_submission_id:
        return []

    current_frappe = _frappe_module()
    attachment_rows = current_frappe.get_all(
        "Attached Document",
        filters={
            "parent": resolved_submission_id,
            "parenttype": "Task Submission",
            "parentfield": "attachments",
        },
        fields=["name", "file", "external_url", "description", "public", "file_name", "file_size"],
        order_by="idx asc",
        limit=0,
    )
    file_name_by_url = _load_submission_file_name_map(resolved_submission_id)
    drive_file_meta_by_file = _load_submission_drive_file_meta_map(list(file_name_by_url.values()))
    return [
        _serialize_task_submission_attachment_row(
            row,
            submission_id=resolved_submission_id,
            file_name_by_url=file_name_by_url,
            drive_file_meta_by_file=drive_file_meta_by_file,
            is_latest_version=is_latest_version,
            version_label=version_label,
        )
        for row in attachment_rows
    ]


def _attachment_is_pdf(attachment_row: dict[str, Any]) -> bool:
    if _clean_text(attachment_row.get("mime_type")) == "application/pdf":
        return True
    explicit_extension = _clean_text(attachment_row.get("extension"))
    if explicit_extension:
        return explicit_extension.lower() == "pdf"
    return extract_file_extension(file_name=attachment_row.get("file_name")) == "pdf"


def _build_annotation_readiness_payload(
    submission_row: dict[str, Any],
    attachments: list[dict[str, Any]],
) -> dict[str, Any]:
    primary_pdf = next((row for row in attachments if _attachment_is_pdf(row)), None)
    if not primary_pdf:
        if _clean_text(submission_row.get("text_content")):
            title = _translate_literal("PDF annotation does not apply to this version")
            message = _translate_literal(
                "This submission version is text-based. Keep feedback in the marking panel until a governed PDF evidence version exists."
            )
        elif _clean_text(submission_row.get("link_url")):
            title = _translate_literal("PDF annotation does not apply to this version")
            message = _translate_literal(
                "This submission version points to linked evidence. Keep review in the drawer and open the linked source directly when needed."
            )
        elif attachments:
            title = _translate_literal("No governed PDF evidence on this version")
            message = _translate_literal(
                "This submission version has attachments, but none are governed PDFs. PDF annotation does not apply to this evidence version."
            )
        else:
            title = _translate_literal("No governed PDF evidence on this version")
            message = _translate_literal(
                "This submission version does not include a governed PDF attachment. Continue grading in the drawer."
            )
        return {
            "mode": "not_applicable",
            "reason_code": "no_pdf_attachment",
            "title": title,
            "message": message,
            "attachment_row_name": None,
            "attachment_file_name": None,
            "preview_status": None,
            "preview_url": None,
            "open_url": None,
        }

    preview_status = _clean_text(primary_pdf.get("preview_status"))
    if preview_status == "ready":
        mode = "reduced"
        reason_code = "pdf_preview_ready"
        title = _translate_literal("Reduced PDF review mode")
        message = _translate_literal(
            "This governed PDF has a preview surface, but text-anchored annotation is not available in the current runtime yet. Review the preview or open the source PDF, then keep marking in the drawer."
        )
    elif preview_status == "pending":
        mode = "reduced"
        reason_code = "pdf_preview_pending"
        title = _translate_literal("Reduced PDF review mode")
        message = _translate_literal(
            "This governed PDF is still generating its preview. Text-anchored annotation is not available in the current runtime yet, so use the source PDF plus drawer marking for now."
        )
    elif preview_status == "failed":
        mode = "unavailable"
        reason_code = "pdf_preview_failed"
        title = _translate_literal("PDF preview unavailable")
        message = _translate_literal(
            "This governed PDF can still be opened, but its preview could not be generated. Keep review action-led for now and continue marking in the drawer."
        )
    elif preview_status == "not_applicable":
        mode = "unavailable"
        reason_code = "pdf_preview_not_applicable"
        title = _translate_literal("PDF preview unavailable")
        message = _translate_literal(
            "This governed PDF does not currently expose a preview surface. Open the source PDF directly and continue marking in the drawer."
        )
    else:
        mode = "reduced"
        reason_code = "pdf_preview_unknown"
        title = _translate_literal("Reduced PDF review mode")
        message = _translate_literal(
            "This governed PDF can be opened for review, but preview/readability metadata is not ready yet. Continue with the source PDF and the drawer marking workflow."
        )

    return {
        "mode": mode,
        "reason_code": reason_code,
        "title": title,
        "message": message,
        "attachment_row_name": _clean_text(primary_pdf.get("row_name")),
        "attachment_file_name": _clean_text(primary_pdf.get("file_name")),
        "preview_status": preview_status,
        "preview_url": _clean_text(primary_pdf.get("preview_url")),
        "open_url": _clean_text(primary_pdf.get("open_url")),
    }


def serialize_task_submission_evidence(
    submission_row: dict[str, Any],
    *,
    is_latest_version: bool | None = None,
) -> dict[str, Any]:
    submission_id = _clean_text(submission_row.get("name"))
    if not submission_id:
        frappe.throw(_("Task Submission is missing identity."), frappe.ValidationError)

    version_value = submission_row.get("version")
    version_label = f"Version {version_value}" if version_value not in (None, "") else None
    attachments = _load_task_submission_attachment_rows(
        submission_id,
        is_latest_version=is_latest_version,
        version_label=version_label,
    )
    return {
        "submission_id": submission_id,
        "version": submission_row.get("version"),
        "submitted_on": submission_row.get("submitted_on"),
        "submitted_by": _clean_text(submission_row.get("submitted_by")),
        "origin": _clean_text(submission_row.get("submission_origin")),
        "is_stub": _bool_flag(submission_row.get("is_stub")),
        "evidence_note": _clean_text(submission_row.get("evidence_note")),
        "is_cloned": _bool_flag(submission_row.get("is_cloned")),
        "cloned_from": _clean_text(submission_row.get("cloned_from")),
        "text_content": submission_row.get("text_content"),
        "link_url": _clean_text(submission_row.get("link_url")),
        "attachments": attachments,
        "annotation_readiness": _build_annotation_readiness_payload(submission_row, attachments),
    }


def _require(value, label):
    if not value:
        frappe.throw(_("{0} is required.").format(label))


def _normalize_payload(payload, kwargs):
    data = payload if payload is not None else kwargs
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw(_("Payload must be a dict."))
    return data


def _require_authenticated():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Not permitted."), frappe.PermissionError)


def _extract_uploaded_files():
    uploads = []
    if not frappe.request or not getattr(frappe.request, "files", None):
        return uploads

    files = []
    if hasattr(frappe.request.files, "getlist"):
        files = frappe.request.files.getlist("files") or []
    if not files:
        single = frappe.request.files.get("file")
        if single:
            files = [single]

    for upload in files:
        filename = getattr(upload, "filename", None)
        content = upload.read()
        if not filename or not content:
            frappe.throw(_("Uploaded files must include a filename and content."))
        uploads.append(
            {
                "file_name": filename,
                "content": content,
            }
        )

    return uploads
