from __future__ import annotations

import os
from typing import Any

import frappe

from ifitwala_ed.integrations.drive.authority import get_current_drive_file_for_slot
from ifitwala_ed.integrations.drive.content_uploads import upload_content_via_drive
from ifitwala_ed.utilities.image_utils import (
    _read_managed_file_bytes,
    _resolve_unique_file_doc_by_url,
)

_PROFILE_IMAGE_SLOT = "profile_image"
_PROFILE_IMAGE_DERIVATIVE_ROLES = ("thumb", "card", "viewer_preview")
_CURRENT_DRIVE_FILE_STATUSES = ("active", "processing", "blocked")
_PROFILE_IMAGE_CONFIG = {
    "Employee": {
        "image_field": "employee_image",
        "subject_arg": "employee",
        "upload_method": "upload_employee_image",
        "preview_method": "request_employee_image_preview_derivatives",
        "sync_field": "employee_image",
    },
    "Student": {
        "image_field": "student_image",
        "subject_arg": "student",
        "upload_method": "upload_student_image",
        "preview_method": "request_student_image_preview_derivatives",
        "sync_field": "student_image",
    },
    "Guardian": {
        "image_field": "guardian_image",
        "subject_arg": "guardian",
        "upload_method": "upload_guardian_image",
        "preview_method": "request_guardian_image_preview_derivatives",
        "sync_field": "guardian_image",
        "organization_field": "organization",
    },
}


def _load_drive_media_api():
    from ifitwala_drive.api import media as drive_media_api

    return drive_media_api


def _log_failure(title: str, payload: dict[str, Any]) -> None:
    frappe.log_error(frappe.as_json(payload, indent=2), title)


def _resolve_current_profile_file(doctype: str, name: str) -> Any | None:
    drive_file = get_current_drive_file_for_slot(
        primary_subject_type=doctype,
        primary_subject_id=name,
        slot=_PROFILE_IMAGE_SLOT,
        fields=["file"],
        statuses=_CURRENT_DRIVE_FILE_STATUSES,
    )
    file_name = str((drive_file or {}).get("file") or "").strip()
    if not file_name or not frappe.db.exists("File", file_name):
        return None
    return frappe.get_doc("File", file_name)


def _sync_profile_field(
    *,
    doctype: str,
    name: str,
    file_url: str,
    organization: str | None = None,
) -> None:
    if doctype == "Guardian":
        frappe.db.set_value(
            "Guardian",
            name,
            {
                "guardian_image": file_url,
                "organization": str(organization or "").strip() or None,
            },
            update_modified=False,
        )
        return

    fieldname = _PROFILE_IMAGE_CONFIG[doctype]["sync_field"]
    frappe.db.set_value(
        doctype,
        name,
        fieldname,
        file_url,
        update_modified=False,
    )

    if doctype == "Student":
        student_doc = frappe.get_doc("Student", name)
        student_doc.student_image = file_url
        if hasattr(student_doc, "sync_student_contact_image"):
            student_doc.sync_student_contact_image()


def _request_preview_derivatives(
    *,
    doctype: str,
    name: str,
    file_id: str,
) -> None:
    drive_media_api = _load_drive_media_api()
    preview_method = getattr(drive_media_api, _PROFILE_IMAGE_CONFIG[doctype]["preview_method"], None)
    if not callable(preview_method):
        return

    payload = {
        _PROFILE_IMAGE_CONFIG[doctype]["subject_arg"]: name,
        "file_id": file_id,
        "derivative_roles": list(_PROFILE_IMAGE_DERIVATIVE_ROLES),
    }
    preview_method(**payload)


def _resolve_source_file_doc(
    *,
    doctype: str,
    name: str,
    fieldname: str,
    original_url: str,
) -> Any | None:
    resolved_url = str(original_url or "").strip()
    filters = {
        "attached_to_doctype": doctype,
        "attached_to_name": name,
        "attached_to_field": fieldname,
    }
    if resolved_url:
        filters["file_url"] = resolved_url

    matches = frappe.get_all(
        "File",
        filters=filters,
        fields=["name"],
        limit=2,
    )
    if len(matches) == 1:
        return frappe.get_doc("File", matches[0]["name"])

    if not resolved_url:
        return None

    source_file_doc = _resolve_unique_file_doc_by_url(resolved_url)
    if source_file_doc:
        return source_file_doc

    matches = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": doctype,
            "attached_to_name": name,
            "file_url": resolved_url,
        },
        fields=["name"],
        limit=2,
    )
    if len(matches) == 1:
        return frappe.get_doc("File", matches[0]["name"])

    return None


def _upload_legacy_profile_image(
    *,
    doctype: str,
    name: str,
    source_file_doc,
    organization: str | None = None,
) -> Any:
    drive_media_api = _load_drive_media_api()
    create_session_callable = getattr(drive_media_api, _PROFILE_IMAGE_CONFIG[doctype]["upload_method"], None)
    if not callable(create_session_callable):
        frappe.throw(f"Drive media API method is unavailable for {doctype} profile image upload.")

    content = _read_managed_file_bytes(source_file_doc, log_label=doctype)
    if not content:
        frappe.throw(f"Could not read legacy {doctype} profile image content.")

    filename = str(source_file_doc.file_name or "").strip() or os.path.basename(
        source_file_doc.file_url or f"{doctype.lower()}_profile_image"
    )
    payload = {
        _PROFILE_IMAGE_CONFIG[doctype]["subject_arg"]: name,
        "upload_source": "API",
    }

    _session_response, _finalize_response, file_doc = upload_content_via_drive(
        create_session_callable=create_session_callable,
        session_payload=payload,
        file_name=filename,
        content=content,
    )
    _sync_profile_field(
        doctype=doctype,
        name=name,
        file_url=file_doc.file_url,
        organization=organization,
    )
    return file_doc


def _repair_profile_image_row(*, doctype: str, row: dict[str, Any]) -> None:
    config = _PROFILE_IMAGE_CONFIG[doctype]
    name = str(row.get("name") or "").strip()
    image_url = str(row.get(config["image_field"]) or "").strip()
    organization = row.get(config.get("organization_field") or "") if config.get("organization_field") else None
    if not name or not image_url:
        return

    current_file_doc = _resolve_current_profile_file(doctype, name)
    if current_file_doc:
        _sync_profile_field(
            doctype=doctype,
            name=name,
            file_url=current_file_doc.file_url,
            organization=organization,
        )
        _request_preview_derivatives(
            doctype=doctype,
            name=name,
            file_id=current_file_doc.name,
        )
        return

    source_file_doc = _resolve_source_file_doc(
        doctype=doctype,
        name=name,
        fieldname=config["image_field"],
        original_url=image_url,
    )
    if not source_file_doc:
        frappe.throw(f"Legacy {doctype} profile image source file could not be resolved.")

    file_doc = _upload_legacy_profile_image(
        doctype=doctype,
        name=name,
        source_file_doc=source_file_doc,
        organization=organization,
    )
    _request_preview_derivatives(
        doctype=doctype,
        name=name,
        file_id=file_doc.name,
    )


def _repair_doctype(doctype: str) -> None:
    if not frappe.db.table_exists(doctype):
        return

    config = _PROFILE_IMAGE_CONFIG[doctype]
    fields = ["name", config["image_field"]]
    organization_field = config.get("organization_field")
    if organization_field:
        fields.append(organization_field)

    rows = frappe.get_all(
        doctype,
        filters={config["image_field"]: ["is", "set"]},
        fields=fields,
        limit=100000,
    )

    for row in rows:
        try:
            _repair_profile_image_row(doctype=doctype, row=row)
        except Exception:
            _log_failure(
                f"{doctype} Profile Image Repair Failed",
                {
                    "error": f"{doctype.lower()}_profile_image_repair_failed",
                    "doctype": doctype,
                    "name": row.get("name"),
                    "image_url": row.get(config["image_field"]),
                    "organization": row.get(organization_field) if organization_field else None,
                },
            )


def execute():
    if not frappe.db.table_exists("File"):
        return

    _repair_doctype("Employee")
    _repair_doctype("Student")
    _repair_doctype("Guardian")
