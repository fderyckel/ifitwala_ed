from __future__ import annotations

import importlib
from typing import Any

import frappe
from frappe import _

from ifitwala_ed.api import file_access as file_access_api
from ifitwala_ed.setup.doctype.org_communication.attachments import (
    ORG_COMMUNICATION_ATTACHMENT_BINDING_ROLE,
    ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX,
    assert_org_communication_attachment_upload_access,
)
from ifitwala_ed.utilities.governed_uploads import (
    _drive_upload_and_finalize,
    _get_uploaded_file,
    _resolve_upload_mime_type_hint,
)


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _load_drive_callable(attribute: str):
    try:
        drive_api = importlib.import_module("ifitwala_drive.api.communications")
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for communication attachments: {0}").format(exc))

    callable_obj = getattr(drive_api, attribute, None)
    if callable(callable_obj):
        return callable_obj

    drive_integration = None
    try:
        drive_integration = importlib.import_module(
            "ifitwala_drive.services.integration.ifitwala_ed_org_communications"
        )
        importlib.reload(drive_integration)
        drive_api = importlib.reload(drive_api)
    except Exception:
        drive_api = importlib.import_module("ifitwala_drive.api.communications")

    callable_obj = getattr(drive_api, attribute, None)
    if callable(callable_obj):
        return callable_obj

    service_attribute = f"{attribute}_service"
    if drive_integration and hasattr(drive_integration, service_attribute):
        service_callable = getattr(drive_integration, service_attribute)

        def _wrapped_service_callable(**kwargs):
            return service_callable(kwargs)

        return _wrapped_service_callable

    frappe.throw(
        _(
            "Ifitwala Drive is missing communications method '{0}'. Deploy or restart the Drive app so the updated communications API is available."
        ).format(attribute)
    )


def _get_attachment_row(doc, row_name: str):
    resolved_row_name = str(row_name or "").strip()
    if not resolved_row_name:
        frappe.throw(_("Attachment row name is required."))

    for row in doc.get("attachments") or []:
        if str(getattr(row, "name", "") or "").strip() == resolved_row_name:
            return row

    frappe.throw(_("Attachment row was not found: {0}").format(resolved_row_name), frappe.DoesNotExistError)


def _get_attachment_preview_status(org_communication: str, row_name: str) -> str | None:
    slot = f"{ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX}{str(row_name or '').strip()}"
    if not slot or not org_communication:
        return None

    drive_file_id = frappe.db.get_value(
        "Drive Binding",
        {
            "binding_doctype": "Org Communication",
            "binding_name": org_communication,
            "binding_role": ORG_COMMUNICATION_ATTACHMENT_BINDING_ROLE,
            "slot": slot,
            "status": "active",
        },
        "drive_file",
    )
    if not drive_file_id:
        drive_file_id = frappe.db.get_value(
            "Drive File",
            {
                "owner_doctype": "Org Communication",
                "owner_name": org_communication,
                "slot": slot,
                "status": "active",
            },
            "name",
        )
    if not drive_file_id:
        return None
    return _clean_text(frappe.db.get_value("Drive File", drive_file_id, "preview_status"))


def _build_attachment_thumbnail_url(org_communication: str, row_name: str, preview_url: str | None) -> str | None:
    thumbnail_builder = getattr(file_access_api, "build_org_communication_attachment_thumbnail_url", None)
    if callable(thumbnail_builder):
        return thumbnail_builder(org_communication=org_communication, row_name=row_name)

    # Older unit-test stubs may only provide preview/open builders.
    return preview_url


def serialize_org_communication_attachment_row(org_communication: str, row) -> dict[str, Any]:
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
                "attached_to_doctype": "Org Communication",
                "attached_to_name": org_communication,
                "file_url": file_url,
            },
            "file_name",
        )

    if file_url:
        preview_status = _get_attachment_preview_status(org_communication, row_name)
        open_url = file_access_api.build_org_communication_attachment_open_url(
            org_communication=org_communication,
            row_name=row_name,
        )
        preview_url = file_access_api.build_org_communication_attachment_preview_url(
            org_communication=org_communication,
            row_name=row_name,
        )
        thumbnail_url = _build_attachment_thumbnail_url(org_communication, row_name, preview_url)
        return {
            "row_name": row_name,
            "kind": "file",
            "title": title,
            "description": description,
            "file_name": file_name or title,
            "file_size": file_size,
            "preview_status": preview_status,
            "thumbnail_url": thumbnail_url,
            "preview_url": preview_url,
            "open_url": open_url,
        }

    return {
        "row_name": row_name,
        "kind": "link",
        "title": title,
        "description": description,
        "external_url": external_url or None,
        "open_url": external_url or None,
    }


@frappe.whitelist()
def upload_org_communication_attachment(
    org_communication: str | None = None,
    row_name: str | None = None,
    **_kwargs,
) -> dict[str, Any]:
    doc = assert_org_communication_attachment_upload_access(
        str(org_communication or "").strip(), permission_type="write"
    )
    filename, content = _get_uploaded_file()
    create_session_callable = _load_drive_callable("upload_org_communication_attachment")

    session_payload = {
        "org_communication": doc.name,
        "row_name": _clean_text(row_name),
        "filename_original": filename,
        "mime_type_hint": _resolve_upload_mime_type_hint(filename=filename),
        "expected_size_bytes": len(content),
        "upload_source": "SPA",
    }
    session_response, finalize_response, _file_doc = _drive_upload_and_finalize(
        create_session_callable=create_session_callable,
        payload=session_payload,
        content=content,
    )

    doc.reload()
    resolved_row_name = (
        _clean_text(finalize_response.get("row_name"))
        or _clean_text(session_response.get("row_name"))
        or _clean_text(row_name)
    )
    target_row = _get_attachment_row(doc, resolved_row_name)

    return {
        "ok": True,
        "org_communication": doc.name,
        "attachment": serialize_org_communication_attachment_row(doc.name, target_row),
    }


@frappe.whitelist()
def add_org_communication_link(
    org_communication: str | None = None,
    external_url: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    doc = assert_org_communication_attachment_upload_access(
        str(org_communication or "").strip(), permission_type="write"
    )
    resolved_url = _clean_text(external_url)
    if not resolved_url:
        frappe.throw(_("External URL is required."))

    row = doc.append(
        "attachments",
        {
            "section_break_sbex": _clean_text(title) or resolved_url,
            "external_url": resolved_url,
            "description": _clean_text(description),
            "public": 0,
        },
    )
    doc.save()
    return {
        "ok": True,
        "org_communication": doc.name,
        "attachment": serialize_org_communication_attachment_row(doc.name, row),
    }


def _mark_binding_inactive(org_communication: str, row_name: str) -> None:
    binding_names = frappe.get_all(
        "Drive Binding",
        filters={
            "binding_doctype": "Org Communication",
            "binding_name": org_communication,
            "binding_role": ORG_COMMUNICATION_ATTACHMENT_BINDING_ROLE,
            "slot": f"{ORG_COMMUNICATION_ATTACHMENT_SLOT_PREFIX}{row_name}",
            "status": "active",
        },
        pluck="name",
    )
    for binding_name in binding_names or []:
        binding_doc = frappe.get_doc("Drive Binding", binding_name)
        binding_doc.status = "inactive"
        binding_doc.save(ignore_permissions=True)


@frappe.whitelist()
def remove_org_communication_attachment(
    org_communication: str | None = None,
    row_name: str | None = None,
) -> dict[str, Any]:
    doc = assert_org_communication_attachment_upload_access(
        str(org_communication or "").strip(), permission_type="write"
    )
    resolved_row_name = str(row_name or "").strip()
    target_row = _get_attachment_row(doc, resolved_row_name)
    if str(getattr(target_row, "file", "") or "").strip():
        _mark_binding_inactive(doc.name, resolved_row_name)

    remaining_rows = [
        row.as_dict() if hasattr(row, "as_dict") else row
        for row in (doc.get("attachments") or [])
        if str(getattr(row, "name", "") or "").strip() != resolved_row_name
    ]
    doc.set("attachments", remaining_rows)
    doc.save()
    return {
        "ok": True,
        "org_communication": doc.name,
        "row_name": resolved_row_name,
    }
