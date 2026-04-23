from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from ifitwala_ed.api.file_access import (
    _require_org_communication_attachment_context,
    _resolve_org_communication_drive_file,
)
from ifitwala_ed.setup.doctype.org_communication.attachments import (
    assert_org_communication_attachment_upload_access,
    build_org_communication_attachment_upload_contract,
    get_org_communication_context_override,
    run_org_communication_post_finalize,
    validate_org_communication_attachment_finalize_context,
)


def upload_org_communication_attachment_access(org_communication: str, *, permission_type: str = "write"):
    return assert_org_communication_attachment_upload_access(org_communication, permission_type=permission_type)


def build_org_communication_upload_contract(
    org_communication_doc,
    *,
    row_name: str | None = None,
) -> dict[str, Any]:
    return build_org_communication_attachment_upload_contract(org_communication_doc, row_name=row_name)


def assert_org_communication_upload_access(org_communication: str, *, permission_type: str = "write"):
    return assert_org_communication_attachment_upload_access(org_communication, permission_type=permission_type)


def assert_org_communication_attachment_read_access(org_communication: str, row_name: str) -> dict[str, Any]:
    resolved_org_communication = str(org_communication or "").strip()
    resolved_row_name = str(row_name or "").strip()
    doc, target_row = _require_org_communication_attachment_context(
        resolved_org_communication,
        resolved_row_name,
    )
    if str(getattr(target_row, "external_url", "") or "").strip():
        frappe.throw(_("External links do not support governed file grants."), frappe.ValidationError)

    file_url = str(getattr(target_row, "file", "") or "").strip()
    if not file_url:
        frappe.throw(_("Attachment file is missing."), frappe.DoesNotExistError)

    drive_file_id, file_id = _resolve_org_communication_drive_file(doc.name, resolved_row_name)
    return {
        "org_communication": doc.name,
        "row_name": resolved_row_name,
        "drive_file_id": drive_file_id,
        "file_id": file_id,
    }


def validate_org_communication_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    return validate_org_communication_attachment_finalize_context(upload_session_doc)


def get_org_communication_attachment_context_override(
    owner_name: str | None, slot: str | None
) -> dict[str, Any] | None:
    return get_org_communication_context_override(owner_name, slot)


def run_org_communication_attachment_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    return run_org_communication_post_finalize(upload_session_doc, created_file)
