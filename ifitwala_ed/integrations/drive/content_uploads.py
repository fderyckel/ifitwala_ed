from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from ifitwala_ed.utilities.governed_uploads import (
    _drive_upload_and_finalize,
    _resolve_upload_mime_type_hint,
)


def upload_content_via_drive(
    *,
    session_payload: dict[str, Any] | None = None,
    workflow_id: str | None = None,
    workflow_payload: dict[str, Any] | None = None,
    file_name: str,
    content: bytes,
    mime_type_hint: str | None = None,
    create_session_callable=None,
    attached_field: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    if create_session_callable is None:
        if not str(workflow_id or "").strip():
            frappe.throw(_("workflow_id is required when using the generic Drive upload session API."))
        try:
            from ifitwala_drive.api import uploads as drive_uploads_api
        except ImportError as exc:
            frappe.throw(_("Ifitwala Drive is required for governed upload execution: {error}").format(error=exc))
        create_session_callable = drive_uploads_api.create_upload_session
        payload = {
            "workflow_id": str(workflow_id or "").strip(),
            "workflow_payload": dict(workflow_payload or {}),
            "filename_original": file_name,
            "mime_type_hint": _resolve_upload_mime_type_hint(
                filename=file_name,
                explicit=mime_type_hint,
            ),
            "expected_size_bytes": len(content or b""),
        }
    else:
        payload = {
            **(session_payload or {}),
            "filename_original": file_name,
            "mime_type_hint": _resolve_upload_mime_type_hint(
                filename=file_name,
                explicit=mime_type_hint,
            ),
            "expected_size_bytes": len(content or b""),
        }
    session_response, finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=create_session_callable,
        payload=payload,
        content=content,
    )

    resolved_attached_field = str(attached_field or "").strip()
    if resolved_attached_field and getattr(file_doc, "attached_to_field", None) != resolved_attached_field:
        frappe.db.set_value(
            "File",
            file_doc.name,
            "attached_to_field",
            resolved_attached_field,
            update_modified=False,
        )
        file_doc.attached_to_field = resolved_attached_field

    return session_response, finalize_response, file_doc
