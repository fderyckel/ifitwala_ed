# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import frappe
from frappe import _

from ifitwala_ed.api import file_access as file_access_api
from ifitwala_ed.api.attachment_previews import extract_file_extension, preview_status_allows_preview
from ifitwala_ed.api.attachment_rows import build_governed_attachment_row
from ifitwala_ed.hr.doctype.expense_claim.receipts import (
    EXPENSE_CLAIM_RECEIPT_BINDING_ROLE,
    EXPENSE_CLAIM_RECEIPT_SLOT_PREFIX,
    assert_expense_claim_receipt_upload_access,
)
from ifitwala_ed.utilities.governed_uploads import (
    _drive_upload_and_finalize,
    _get_uploaded_file,
    _resolve_upload_mime_type_hint,
    _workflow_result_payload,
)

EXPENSE_CLAIM_RECEIPT_SURFACE = "expense_claim.receipt"
EXPENSE_CLAIM_RECEIPT_WORKFLOW_ID = "expense_claim.receipt"


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_expense_claim_receipt_open_url(*, expense_claim: str, row_name: str) -> str | None:
    resolved_expense_claim = _clean_text(expense_claim)
    resolved_row_name = _clean_text(row_name)
    if not resolved_expense_claim or not resolved_row_name:
        return None
    return "/api/method/ifitwala_ed.api.expense_claim_receipts.open_expense_claim_receipt?" + urlencode(
        {"expense_claim": resolved_expense_claim, "row_name": resolved_row_name}
    )


def build_expense_claim_receipt_preview_url(*, expense_claim: str, row_name: str) -> str | None:
    resolved_expense_claim = _clean_text(expense_claim)
    resolved_row_name = _clean_text(row_name)
    if not resolved_expense_claim or not resolved_row_name:
        return None
    return "/api/method/ifitwala_ed.api.expense_claim_receipts.preview_expense_claim_receipt?" + urlencode(
        {"expense_claim": resolved_expense_claim, "row_name": resolved_row_name}
    )


def build_expense_claim_receipt_thumbnail_url(*, expense_claim: str, row_name: str) -> str | None:
    resolved_expense_claim = _clean_text(expense_claim)
    resolved_row_name = _clean_text(row_name)
    if not resolved_expense_claim or not resolved_row_name:
        return None
    return "/api/method/ifitwala_ed.api.expense_claim_receipts.thumbnail_expense_claim_receipt?" + urlencode(
        {"expense_claim": resolved_expense_claim, "row_name": resolved_row_name}
    )


def _resolve_expense_claim_receipt_drive_file(expense_claim: str, row_name: str) -> tuple[str, str | None]:
    row_slot = f"{EXPENSE_CLAIM_RECEIPT_SLOT_PREFIX}{row_name}"
    drive_file = frappe.db.get_value(
        "Drive Binding",
        {
            "binding_doctype": "Expense Claim",
            "binding_name": expense_claim,
            "binding_role": EXPENSE_CLAIM_RECEIPT_BINDING_ROLE,
            "slot": row_slot,
            "status": "active",
        },
        ["drive_file", "file"],
        as_dict=True,
    )
    if drive_file and drive_file.get("drive_file"):
        return drive_file.get("drive_file"), _clean_text(drive_file.get("file"))

    drive_file = frappe.db.get_value(
        "Drive File",
        {
            "owner_doctype": "Expense Claim",
            "owner_name": expense_claim,
            "slot": row_slot,
            "status": "active",
        },
        ["name", "file"],
        as_dict=True,
    )
    if drive_file and drive_file.get("name"):
        return drive_file.get("name"), _clean_text(drive_file.get("file"))

    frappe.throw(_("Governed receipt file was not found."), frappe.DoesNotExistError)


def _get_receipt_render_meta(expense_claim: str, row_name: str) -> dict[str, Any]:
    slot = f"{EXPENSE_CLAIM_RECEIPT_SLOT_PREFIX}{str(row_name or '').strip()}"
    if not slot or not expense_claim:
        return {"preview_status": None, "inline_preview_ready": False}

    drive_file_id = frappe.db.get_value(
        "Drive Binding",
        {
            "binding_doctype": "Expense Claim",
            "binding_name": expense_claim,
            "binding_role": EXPENSE_CLAIM_RECEIPT_BINDING_ROLE,
            "slot": slot,
            "status": "active",
        },
        "drive_file",
    )
    if not drive_file_id:
        drive_file_id = frappe.db.get_value(
            "Drive File",
            {
                "owner_doctype": "Expense Claim",
                "owner_name": expense_claim,
                "slot": slot,
                "status": "active",
            },
            "name",
        )
    if not drive_file_id:
        return {"preview_status": None, "inline_preview_ready": False}

    drive_file = (
        frappe.db.get_value(
            "Drive File",
            drive_file_id,
            ["preview_status", "current_version"],
            as_dict=True,
        )
        or {}
    )
    preview_status = _clean_text(drive_file.get("preview_status"))
    return {
        "preview_status": preview_status,
        "inline_preview_ready": preview_status == "ready",
    }


def serialize_expense_claim_receipt_row(expense_claim: str, row) -> dict[str, Any]:
    row_name = str(getattr(row, "name", "") or "").strip()
    file_url = str(getattr(row, "file", "") or "").strip()
    external_url = str(getattr(row, "external_url", "") or "").strip()
    title = _clean_text(getattr(row, "section_break_sbex", None))
    description = _clean_text(getattr(row, "description", None))
    file_name = _clean_text(getattr(row, "file_name", None))
    file_size = getattr(row, "file_size", None)

    if not title:
        title = file_name or external_url or row_name

    if file_url and not file_name:
        file_name = frappe.db.get_value(
            "File",
            {
                "attached_to_doctype": "Expense Claim",
                "attached_to_name": expense_claim,
                "file_url": file_url,
            },
            "file_name",
        )

    if file_url:
        preview_meta = _get_receipt_render_meta(expense_claim, row_name)
        preview_status = preview_meta.get("preview_status")
        open_url = build_expense_claim_receipt_open_url(expense_claim=expense_claim, row_name=row_name)
        preview_url = build_expense_claim_receipt_preview_url(expense_claim=expense_claim, row_name=row_name)
        if not preview_status_allows_preview(preview_status):
            preview_url = None
        thumbnail_url = (
            build_expense_claim_receipt_thumbnail_url(expense_claim=expense_claim, row_name=row_name)
            if preview_meta.get("inline_preview_ready")
            else None
        )
        attachment = build_governed_attachment_row(
            row_id=row_name,
            surface=EXPENSE_CLAIM_RECEIPT_SURFACE,
            item_id=row_name,
            owner_doctype="Expense Claim",
            owner_name=expense_claim,
            display_name=title,
            description=description,
            extension=extract_file_extension(file_name=file_name, file_url=file_url),
            size_bytes=file_size,
            preview_status=preview_status,
            thumbnail_url=thumbnail_url,
            preview_url=preview_url,
            open_url=open_url,
            download_url=open_url,
        )
        return {
            "row_name": row_name,
            "kind": "file",
            "title": title,
            "description": description,
            "file_name": file_name or title,
            "file_size": file_size,
            "attachment": attachment,
        }

    attachment = build_governed_attachment_row(
        row_id=row_name,
        surface=EXPENSE_CLAIM_RECEIPT_SURFACE,
        item_id=row_name,
        owner_doctype="Expense Claim",
        owner_name=expense_claim,
        link_url=external_url,
        display_name=title,
        description=description,
        open_url=external_url,
    )
    return {
        "row_name": row_name,
        "kind": "link",
        "title": title,
        "description": description,
        "external_url": external_url or None,
        "attachment": attachment,
    }


def _get_receipt_row(doc, row_name: str):
    resolved_row_name = str(row_name or "").strip()
    if not resolved_row_name:
        frappe.throw(_("Receipt row name is required."))

    for row in doc.get("receipts") or []:
        if str(getattr(row, "name", "") or "").strip() == resolved_row_name:
            return row

    frappe.throw(
        _("Receipt row was not found: {row_name}").format(row_name=resolved_row_name),
        frappe.DoesNotExistError,
    )


def _create_expense_claim_receipt_session(**payload):
    try:
        from ifitwala_drive.api import uploads as drive_uploads_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for expense claim receipts: {error}").format(error=exc))

    workflow_payload = payload.get("workflow_payload")
    if not isinstance(workflow_payload, dict):
        workflow_payload = {
            "expense_claim": payload.get("expense_claim"),
            "row_name": payload.get("row_name"),
        }

    return drive_uploads_api.create_upload_session(
        workflow_id=EXPENSE_CLAIM_RECEIPT_WORKFLOW_ID,
        workflow_payload=workflow_payload,
        filename_original=payload.get("filename_original"),
        mime_type_hint=payload.get("mime_type_hint"),
        expected_size_bytes=payload.get("expected_size_bytes"),
        idempotency_key=payload.get("idempotency_key"),
        upload_source=payload.get("upload_source"),
    )


@frappe.whitelist()
def upload_expense_claim_receipt(
    expense_claim: str | None = None,
    row_name: str | None = None,
    **_kwargs,
) -> dict[str, Any]:
    doc = assert_expense_claim_receipt_upload_access(str(expense_claim or "").strip(), permission_type="write")
    filename, content = _get_uploaded_file()
    workflow_payload = {
        "expense_claim": doc.name,
        "row_name": _clean_text(row_name),
    }
    session_response, finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=_create_expense_claim_receipt_session,
        payload={
            "workflow_id": EXPENSE_CLAIM_RECEIPT_WORKFLOW_ID,
            "workflow_payload": workflow_payload,
            "expense_claim": doc.name,
            "row_name": _clean_text(row_name),
            "filename_original": filename,
            "mime_type_hint": _resolve_upload_mime_type_hint(filename=filename),
            "expected_size_bytes": len(content),
            "upload_source": "SPA",
        },
        content=content,
    )
    del file_doc

    doc.reload()
    session_workflow_result = _workflow_result_payload(session_response)
    finalize_workflow_result = _workflow_result_payload(finalize_response)
    resolved_row_name = (
        _clean_text(finalize_workflow_result.get("row_name"))
        or _clean_text(session_workflow_result.get("row_name"))
        or _clean_text(row_name)
    )
    target_row = _get_receipt_row(doc, resolved_row_name)

    return {
        "ok": True,
        "expense_claim": doc.name,
        "receipt": serialize_expense_claim_receipt_row(doc.name, target_row),
    }


@frappe.whitelist()
def add_expense_claim_receipt_link(
    expense_claim: str | None = None,
    external_url: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    doc = assert_expense_claim_receipt_upload_access(str(expense_claim or "").strip(), permission_type="write")
    resolved_url = _clean_text(external_url)
    if not resolved_url:
        frappe.throw(_("External URL is required."))

    row = doc.append(
        "receipts",
        {
            "section_break_sbex": _clean_text(title) or resolved_url,
            "external_url": resolved_url,
            "description": _clean_text(description),
            "public": 0,
        },
    )
    doc.flags.ignore_expense_claim_lock = True
    doc.save(ignore_permissions=True)
    return {
        "ok": True,
        "expense_claim": doc.name,
        "receipt": serialize_expense_claim_receipt_row(doc.name, row),
    }


def _mark_binding_inactive(expense_claim: str, row_name: str) -> None:
    binding_names = frappe.get_all(
        "Drive Binding",
        filters={
            "binding_doctype": "Expense Claim",
            "binding_name": expense_claim,
            "binding_role": EXPENSE_CLAIM_RECEIPT_BINDING_ROLE,
            "slot": f"{EXPENSE_CLAIM_RECEIPT_SLOT_PREFIX}{row_name}",
            "status": "active",
        },
        pluck="name",
    )
    for binding_name in binding_names or []:
        binding_doc = frappe.get_doc("Drive Binding", binding_name)
        binding_doc.status = "inactive"
        binding_doc.save(ignore_permissions=True)


@frappe.whitelist()
def remove_expense_claim_receipt(
    expense_claim: str | None = None,
    row_name: str | None = None,
) -> dict[str, Any]:
    doc = assert_expense_claim_receipt_upload_access(str(expense_claim or "").strip(), permission_type="write")
    resolved_row_name = str(row_name or "").strip()
    target_row = _get_receipt_row(doc, resolved_row_name)
    if str(getattr(target_row, "file", "") or "").strip():
        _mark_binding_inactive(doc.name, resolved_row_name)

    remaining_rows = [
        row.as_dict() if hasattr(row, "as_dict") else row
        for row in (doc.get("receipts") or [])
        if str(getattr(row, "name", "") or "").strip() != resolved_row_name
    ]
    doc.set("receipts", remaining_rows)
    doc.flags.ignore_expense_claim_lock = True
    doc.save(ignore_permissions=True)
    return {
        "ok": True,
        "expense_claim": doc.name,
        "row_name": resolved_row_name,
    }


def _require_receipt_context(expense_claim: str, row_name: str):
    resolved_expense_claim = str(expense_claim or "").strip()
    resolved_row_name = str(row_name or "").strip()
    if not resolved_expense_claim:
        frappe.throw(_("Expense Claim is required."), frappe.ValidationError)
    if not resolved_row_name:
        frappe.throw(_("Receipt row name is required."), frappe.ValidationError)

    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to access this receipt."), frappe.PermissionError)

    doc = frappe.get_doc("Expense Claim", resolved_expense_claim)
    if not frappe.has_permission("Expense Claim", doc=doc, ptype="read"):
        frappe.throw(_("You do not have permission to access this receipt."), frappe.PermissionError)

    target_row = _get_receipt_row(doc, resolved_row_name)
    return doc, target_row


def _resolve_receipt_target_url(
    *,
    expense_claim: str,
    row_name: str,
    prefer_preview: bool = False,
    derivative_role: str | None = None,
    strict_derivative: bool = False,
) -> str | None:
    drive_file_id, file_id = _resolve_expense_claim_receipt_drive_file(expense_claim, row_name)
    return file_access_api._resolve_drive_file_grant_target_url(
        drive_file_id=drive_file_id,
        file_id=file_id or "",
        prefer_preview=prefer_preview,
        derivative_role=derivative_role,
        strict_derivative=strict_derivative,
    )


@frappe.whitelist()
def open_expense_claim_receipt(
    expense_claim: str | None = None,
    row_name: str | None = None,
):
    doc, target_row = _require_receipt_context(str(expense_claim or ""), str(row_name or ""))

    external_url = str(getattr(target_row, "external_url", "") or "").strip()
    if external_url:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = external_url
        return

    if not str(getattr(target_row, "file", "") or "").strip():
        frappe.throw(_("Receipt file is missing."), frappe.DoesNotExistError)

    target_url = _resolve_receipt_target_url(expense_claim=doc.name, row_name=target_row.name)
    if file_access_api._respond_with_delivery_target(target_url=target_url):
        return

    frappe.throw(_("Could not resolve the receipt."), frappe.DoesNotExistError)


@frappe.whitelist()
def preview_expense_claim_receipt(
    expense_claim: str | None = None,
    row_name: str | None = None,
):
    doc, target_row = _require_receipt_context(str(expense_claim or ""), str(row_name or ""))

    if str(getattr(target_row, "external_url", "") or "").strip():
        frappe.throw(_("External links do not support governed preview."), frappe.ValidationError)
    if not str(getattr(target_row, "file", "") or "").strip():
        frappe.throw(_("Receipt file is missing."), frappe.DoesNotExistError)

    target_url = _resolve_receipt_target_url(
        expense_claim=doc.name,
        row_name=target_row.name,
        prefer_preview=True,
    )
    if file_access_api._respond_with_delivery_target(target_url=target_url):
        return

    frappe.throw(_("Could not resolve the receipt preview."), frappe.DoesNotExistError)


@frappe.whitelist()
def thumbnail_expense_claim_receipt(
    expense_claim: str | None = None,
    row_name: str | None = None,
):
    doc, target_row = _require_receipt_context(str(expense_claim or ""), str(row_name or ""))

    if str(getattr(target_row, "external_url", "") or "").strip():
        frappe.throw(_("External links do not support governed thumbnails."), frappe.ValidationError)
    if not str(getattr(target_row, "file", "") or "").strip():
        frappe.throw(_("Receipt file is missing."), frappe.DoesNotExistError)

    drive_file_id, file_id = _resolve_expense_claim_receipt_drive_file(doc.name, target_row.name)
    derivative_role = file_access_api._resolve_card_preview_derivative_role_for_drive_file(drive_file_id)
    target_url = file_access_api._resolve_cached_thumbnail_target_url(
        drive_file_id=drive_file_id,
        file_id=file_id or "",
        surface_parts=["expense_claim", doc.name, target_row.name],
        derivative_role=derivative_role,
        strict_derivative=True,
        target_resolver=lambda: _resolve_receipt_target_url(
            expense_claim=doc.name,
            row_name=target_row.name,
            prefer_preview=True,
            derivative_role=derivative_role,
            strict_derivative=True,
        ),
    )
    if target_url and file_access_api._respond_with_delivery_target(target_url=target_url, cache_headers=True):
        return

    frappe.throw(_("Could not resolve the receipt thumbnail."), frappe.DoesNotExistError)
