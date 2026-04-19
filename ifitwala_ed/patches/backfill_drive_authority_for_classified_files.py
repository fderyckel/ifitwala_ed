from __future__ import annotations

import hashlib
import mimetypes
import os
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

_CLASSIFICATION_FIELDS = [
    "name",
    "file",
    "attached_doctype",
    "attached_name",
    "primary_subject_type",
    "primary_subject_id",
    "data_class",
    "purpose",
    "retention_policy",
    "slot",
    "organization",
    "school",
    "version_number",
    "is_current_version",
    "content_hash",
    "upload_source",
    "erasure_state",
    "legal_hold",
    "owner",
]
_FILE_FIELDS = [
    "name",
    "file_url",
    "file_name",
    "file_size",
    "is_private",
    "attached_to_doctype",
    "attached_to_name",
    "owner",
]
_OWNER_FROM_ATTACHMENT = {"Task Submission", "Task", "Supporting Material", "Org Communication"}
_OWNER_FROM_SUBJECT = {"Employee", "Guardian", "Student", "Student Applicant"}
_VALID_UPLOAD_SOURCES = {"Desk", "SPA", "API", "Job"}
_BINDING_ELIGIBLE_STATUSES = {"active", "blocked"}


def _load_drive_dependencies():
    from ifitwala_drive.services.files.creation import create_drive_file_artifacts
    from ifitwala_drive.services.storage.base import get_storage_backend
    from ifitwala_drive.services.uploads.keys import build_upload_object_key

    return create_drive_file_artifacts, get_storage_backend, build_upload_object_key


def _load_classification_rows() -> list[dict[str, Any]]:
    return (
        frappe.get_all(
            "File Classification",
            fields=_CLASSIFICATION_FIELDS,
            order_by="primary_subject_type asc, primary_subject_id asc, slot asc, is_current_version asc, version_number asc, creation asc",
            limit=100000,
        )
        or []
    )


def _load_file_rows(file_names: list[str]) -> dict[str, dict[str, Any]]:
    if not file_names:
        return {}

    rows = (
        frappe.get_all(
            "File",
            filters={"name": ["in", file_names]},
            fields=_FILE_FIELDS,
            limit=100000,
        )
        or []
    )
    return {str(row.get("name") or "").strip(): row for row in rows}


def _load_existing_drive_files(file_names: list[str]) -> set[str]:
    if not file_names:
        return set()

    rows = (
        frappe.get_all(
            "Drive File",
            filters={"file": ["in", file_names]},
            fields=["file"],
            limit=100000,
        )
        or []
    )
    return {str(row.get("file") or "").strip() for row in rows if str(row.get("file") or "").strip()}


def _resolve_owner_context(classification_row: dict[str, Any], file_row: dict[str, Any]) -> tuple[str, str]:
    attached_doctype = str(
        classification_row.get("attached_doctype") or file_row.get("attached_to_doctype") or ""
    ).strip()
    attached_name = str(classification_row.get("attached_name") or file_row.get("attached_to_name") or "").strip()
    primary_subject_type = str(classification_row.get("primary_subject_type") or "").strip()
    primary_subject_id = str(classification_row.get("primary_subject_id") or "").strip()
    organization = str(classification_row.get("organization") or "").strip()

    if attached_doctype in _OWNER_FROM_ATTACHMENT and attached_name:
        return attached_doctype, attached_name
    if primary_subject_type in _OWNER_FROM_SUBJECT and primary_subject_id:
        return primary_subject_type, primary_subject_id
    if organization:
        return "Organization", organization
    if attached_doctype and attached_name:
        return attached_doctype, attached_name

    frappe.throw(
        _("Cannot infer Drive owner context for File Classification '{classification}'.").format(
            classification=classification_row.get("name") or _("unknown")
        )
    )


def _normalize_upload_source(value: str | None) -> str:
    resolved = str(value or "").strip()
    return resolved if resolved in _VALID_UPLOAD_SOURCES else "API"


def _resolve_created_by_user(classification_row: dict[str, Any], file_row: dict[str, Any]) -> str:
    for candidate in (
        classification_row.get("owner"),
        file_row.get("owner"),
        getattr(getattr(frappe, "session", None), "user", None),
        "Administrator",
    ):
        user = str(candidate or "").strip()
        if user and frappe.db.exists("User", user):
            return user
    return "Administrator"


def _resolve_file_name(file_row: dict[str, Any]) -> str:
    file_name = str(file_row.get("file_name") or "").strip()
    if file_name:
        return file_name

    file_url = str(file_row.get("file_url") or "").strip().rstrip("/")
    if file_url:
        return file_url.rsplit("/", 1)[-1]

    return "upload.bin"


def _legacy_session_key(classification_row: dict[str, Any]) -> str:
    seed = "|".join(
        [
            "legacy-file-classification-backfill",
            str(classification_row.get("name") or "").strip(),
            str(classification_row.get("file") or "").strip(),
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _resolve_local_path(file_url: str | None) -> str | None:
    value = str(file_url or "").strip()
    if not value or value.startswith("http"):
        return None

    relative_path = value.lstrip("/")
    if relative_path.startswith("private/") or relative_path.startswith("public/"):
        return frappe.get_site_path(relative_path)

    base = "private" if value.startswith("/private/") else "public"
    return frappe.get_site_path(base, relative_path)


def _read_file_bytes(file_row: dict[str, Any]) -> bytes:
    local_path = _resolve_local_path(file_row.get("file_url"))
    if not local_path or not os.path.exists(local_path):
        file_name = str(file_row.get("name") or "").strip()
        frappe.throw(_("Legacy governed file is missing its local blob: {file_name}").format(file_name=file_name))

    with open(local_path, "rb") as handle:
        return handle.read()


def _resolve_content_hash(classification_row: dict[str, Any], content: bytes) -> str:
    existing = str(classification_row.get("content_hash") or "").strip()
    if existing:
        return existing
    return hashlib.sha256(content).hexdigest()


def _resolve_mime_type(file_row: dict[str, Any]) -> str | None:
    file_name = _resolve_file_name(file_row)
    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type or None


def _get_or_create_upload_session(
    *,
    classification_row: dict[str, Any],
    file_row: dict[str, Any],
    owner_doctype: str,
    owner_name: str,
) -> Any:
    session_key = _legacy_session_key(classification_row)
    existing = frappe.db.get_value("Drive Upload Session", {"session_key": session_key}, "name")
    if existing:
        return frappe.get_doc("Drive Upload Session", existing)

    file_name = _resolve_file_name(file_row)
    session_doc = frappe.get_doc(
        {
            "doctype": "Drive Upload Session",
            "session_key": session_key,
            "status": "uploaded",
            "upload_source": _normalize_upload_source(classification_row.get("upload_source")),
            "created_by_user": _resolve_created_by_user(classification_row, file_row),
            "attached_doctype": str(
                classification_row.get("attached_doctype") or file_row.get("attached_to_doctype") or ""
            ).strip(),
            "attached_name": str(
                classification_row.get("attached_name") or file_row.get("attached_to_name") or ""
            ).strip(),
            "owner_doctype": owner_doctype,
            "owner_name": owner_name,
            "organization": classification_row.get("organization"),
            "school": classification_row.get("school"),
            "intended_primary_subject_type": classification_row.get("primary_subject_type"),
            "intended_primary_subject_id": classification_row.get("primary_subject_id"),
            "intended_data_class": classification_row.get("data_class"),
            "intended_purpose": classification_row.get("purpose"),
            "intended_retention_policy": classification_row.get("retention_policy"),
            "intended_slot": classification_row.get("slot"),
            "filename_original": file_name,
            "mime_type_hint": _resolve_mime_type(file_row),
            "is_private": int(bool(file_row.get("is_private"))),
            "expires_on": now_datetime(),
        }
    )
    session_doc.insert(ignore_permissions=True)
    return session_doc


def _resolve_status(classification_row: dict[str, Any]) -> str:
    erasure_state = str(classification_row.get("erasure_state") or "active").strip() or "active"
    if erasure_state == "erased":
        return "erased"
    if erasure_state == "blocked_legal" or int(classification_row.get("legal_hold") or 0):
        return "blocked"
    if not int(classification_row.get("is_current_version") or 0):
        return "superseded"
    return "active"


def _resolve_binding_role(upload_session_doc) -> str | None:
    from ifitwala_ed.integrations.drive import bridge

    contract = bridge.resolve_finalize_contract(upload_session_doc)
    return str(contract.get("binding_role") or "").strip() or None


def _persist_drive_metadata(
    *,
    upload_session_doc,
    classification_row: dict[str, Any],
    file_row: dict[str, Any],
    drive_artifacts: dict[str, Any],
    content_hash: str,
    size_bytes: int,
) -> None:
    drive_file_id = drive_artifacts["drive_file_id"]
    drive_file_doc = frappe.get_doc("Drive File", drive_file_id)
    drive_file_doc.legal_hold = int(classification_row.get("legal_hold") or 0)
    drive_file_doc.erasure_state = str(classification_row.get("erasure_state") or "active").strip() or "active"
    drive_file_doc.status = _resolve_status(classification_row)
    drive_file_doc.content_hash = content_hash
    drive_file_doc.is_private = int(bool(file_row.get("is_private")))
    drive_file_doc.save(ignore_permissions=True)

    upload_session_doc.received_size_bytes = size_bytes
    upload_session_doc.content_hash = content_hash
    upload_session_doc.storage_backend = drive_file_doc.storage_backend
    upload_session_doc.file = file_row.get("name")
    upload_session_doc.drive_file = drive_file_id
    upload_session_doc.drive_file_version = drive_artifacts.get("drive_file_version_id")
    upload_session_doc.canonical_ref = drive_artifacts.get("canonical_ref")
    upload_session_doc.status = "completed"
    upload_session_doc.completed_on = now_datetime()
    upload_session_doc.save(ignore_permissions=True)


def _backfill_single_row(
    *,
    classification_row: dict[str, Any],
    file_row: dict[str, Any],
) -> None:
    create_drive_file_artifacts, get_storage_backend, build_upload_object_key = _load_drive_dependencies()

    owner_doctype, owner_name = _resolve_owner_context(classification_row, file_row)
    upload_session_doc = _get_or_create_upload_session(
        classification_row=classification_row,
        file_row=file_row,
        owner_doctype=owner_doctype,
        owner_name=owner_name,
    )
    content = _read_file_bytes(file_row)
    content_hash = _resolve_content_hash(classification_row, content)
    size_bytes = int(file_row.get("file_size") or 0) or len(content)
    resolved_status = _resolve_status(classification_row)

    storage = get_storage_backend()
    object_key = build_upload_object_key(
        session_key=upload_session_doc.session_key,
        owner_doctype=upload_session_doc.owner_doctype,
        owner_name=upload_session_doc.owner_name,
        attached_doctype=upload_session_doc.attached_doctype,
        attached_name=upload_session_doc.attached_name,
        slot=upload_session_doc.intended_slot,
        filename=upload_session_doc.filename_original,
    )
    storage_artifact = storage.write_final_object(
        object_key=object_key,
        content=content,
        mime_type=upload_session_doc.mime_type_hint,
    )
    storage_artifact["storage_backend"] = storage_artifact.get("storage_backend") or storage.backend_name
    storage_artifact["size_bytes"] = size_bytes
    storage_artifact["content_hash"] = content_hash
    if upload_session_doc.mime_type_hint:
        storage_artifact["mime_type"] = upload_session_doc.mime_type_hint

    drive_artifacts = create_drive_file_artifacts(
        upload_session_doc=upload_session_doc,
        file_id=file_row["name"],
        storage_artifact=storage_artifact,
        binding_role=(
            _resolve_binding_role(upload_session_doc) if resolved_status in _BINDING_ELIGIBLE_STATUSES else None
        ),
    )
    _persist_drive_metadata(
        upload_session_doc=upload_session_doc,
        classification_row=classification_row,
        file_row=file_row,
        drive_artifacts=drive_artifacts,
        content_hash=content_hash,
        size_bytes=size_bytes,
    )


def execute():
    required_tables = {
        "File Classification",
        "File",
        "Drive Upload Session",
        "Drive File",
        "Drive File Version",
    }
    if not all(frappe.db.table_exists(doctype) for doctype in required_tables):
        return

    classification_rows = _load_classification_rows()
    if not classification_rows:
        return

    file_names = [
        str(row.get("file") or "").strip() for row in classification_rows if str(row.get("file") or "").strip()
    ]
    file_rows = _load_file_rows(file_names)
    existing_drive_files = _load_existing_drive_files(file_names)

    failures: list[tuple[str, str]] = []
    for classification_row in classification_rows:
        file_name = str(classification_row.get("file") or "").strip()
        if not file_name or file_name in existing_drive_files:
            continue

        file_row = file_rows.get(file_name)
        if not file_row:
            failures.append((file_name or str(classification_row.get("name") or "").strip(), "file_row_missing"))
            continue

        try:
            _backfill_single_row(classification_row=classification_row, file_row=file_row)
            existing_drive_files.add(file_name)
        except Exception:
            log_error = getattr(frappe, "log_error", None)
            get_traceback = getattr(frappe, "get_traceback", None)
            trace = get_traceback() if callable(get_traceback) else f"legacy_drive_backfill_failed: {file_name}"
            if callable(log_error):
                log_error(
                    trace,
                    "Legacy Drive Authority Backfill Failed",
                )
            failures.append((file_name, trace))

    if failures:
        sample = ", ".join(name for name, _error in failures[:5])
        remaining = max(0, len(failures) - 5)
        suffix = _(" (+{0} more)").format(remaining) if remaining else ""
        frappe.throw(
            _(
                "Drive authority backfill failed for legacy classified files: {sample}{suffix}. See Error Log for details."
            ).format(sample=sample or _("unknown files"), suffix=suffix)
        )
