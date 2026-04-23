from __future__ import annotations

import frappe
from ifitwala_drive.services.storage.base import get_storage_backend

from ifitwala_ed.patches import repair_governed_profile_images

_PROFILE_IMAGE_SLOT = "profile_image"
_PROFILE_IMAGE_SUBJECT_TYPES = ("Employee", "Student", "Guardian")
_CURRENT_PROFILE_IMAGE_STATUSES = ("active", "processing", "blocked")


def _compute_private_file_url(*, storage_backend: str | None, object_key: str | None) -> str | None:
    resolved_object_key = str(object_key or "").strip()
    if not resolved_object_key:
        return None

    try:
        backend = get_storage_backend(storage_backend or None)
    except Exception:
        return None

    builder = getattr(backend, "_build_private_file_url", None)
    if not callable(builder):
        return None
    try:
        return str(builder(resolved_object_key) or "").strip() or None
    except Exception:
        return None


def _normalize_drive_file_rows() -> None:
    if not frappe.db.table_exists("Drive File"):
        return

    rows = frappe.get_all(
        "Drive File",
        filters={
            "slot": _PROFILE_IMAGE_SLOT,
            "primary_subject_type": ["in", list(_PROFILE_IMAGE_SUBJECT_TYPES)],
        },
        fields=[
            "name",
            "file",
            "source_upload_session",
            "storage_backend",
            "storage_object_key",
        ],
        limit=0,
    )

    for row in rows:
        drive_file_name = str(row.get("name") or "").strip()
        file_name = str(row.get("file") or "").strip()
        upload_session_name = str(row.get("source_upload_session") or "").strip()
        if not drive_file_name:
            continue

        frappe.db.set_value(
            "Drive File",
            drive_file_name,
            "is_private",
            1,
            update_modified=False,
        )

        if file_name and frappe.db.exists("File", file_name):
            values: dict[str, object] = {"is_private": 1}
            private_file_url = _compute_private_file_url(
                storage_backend=row.get("storage_backend"),
                object_key=row.get("storage_object_key"),
            )
            if private_file_url:
                values["file_url"] = private_file_url
            frappe.db.set_value(
                "File",
                file_name,
                values,
                update_modified=False,
            )

        if upload_session_name and frappe.db.exists("Drive Upload Session", upload_session_name):
            frappe.db.set_value(
                "Drive Upload Session",
                upload_session_name,
                "is_private",
                1,
                update_modified=False,
            )


def _sync_current_profile_fields() -> None:
    if not frappe.db.table_exists("Drive File"):
        return

    rows = frappe.get_all(
        "Drive File",
        filters={
            "slot": _PROFILE_IMAGE_SLOT,
            "primary_subject_type": ["in", list(_PROFILE_IMAGE_SUBJECT_TYPES)],
            "status": ["in", list(_CURRENT_PROFILE_IMAGE_STATUSES)],
        },
        fields=["primary_subject_type", "primary_subject_id"],
        limit=0,
    )

    subjects = sorted(
        {
            (
                str(row.get("primary_subject_type") or "").strip(),
                str(row.get("primary_subject_id") or "").strip(),
            )
            for row in rows
            if str(row.get("primary_subject_type") or "").strip() and str(row.get("primary_subject_id") or "").strip()
        }
    )

    for doctype, name in subjects:
        current_file_doc = repair_governed_profile_images._resolve_current_profile_file(doctype, name)
        if not current_file_doc:
            continue

        organization = None
        if doctype == "Guardian":
            organization = frappe.db.get_value("Guardian", name, "organization")

        repair_governed_profile_images._sync_profile_field(
            doctype=doctype,
            name=name,
            file_url=current_file_doc.file_url,
            organization=organization,
        )


def execute() -> None:
    _normalize_drive_file_rows()
    _sync_current_profile_fields()
