from __future__ import annotations

from typing import Any

import frappe
from frappe import _

_REQUIRED_TABLES = {"Drive File", "Drive Upload Session", "Drive Binding"}
_BINDING_ELIGIBLE_STATUSES = {"active", "blocked", "processing"}
_ORGANIZATION_MEDIA_SLOT_PREFIXES = (
    "organization_media__",
    "organization_logo__",
    "school_logo__",
    "school_gallery_image__",
)


def _load_candidate_drive_files() -> list[dict[str, Any]]:
    return (
        frappe.get_all(
            "Drive File",
            filters={"status": ["in", sorted(_BINDING_ELIGIBLE_STATUSES)]},
            fields=[
                "name",
                "file",
                "source_upload_session",
                "status",
                "attached_doctype",
                "attached_name",
                "owner_doctype",
                "owner_name",
                "organization",
                "school",
                "primary_subject_type",
                "primary_subject_id",
                "slot",
            ],
            limit=100000,
        )
        or []
    )


def _has_active_primary_binding(drive_file_id: str) -> bool:
    return bool(
        frappe.db.get_value(
            "Drive Binding",
            {
                "drive_file": drive_file_id,
                "is_primary": 1,
                "status": "active",
            },
            "name",
        )
    )


def _resolve_binding_role(upload_session_doc) -> str | None:
    from ifitwala_ed.integrations.drive import bridge

    contract = bridge.resolve_finalize_contract(upload_session_doc)
    return str(contract.get("binding_role") or "").strip() or None


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _hydrate_upload_session_context(upload_session_doc, drive_file_row: dict[str, Any]) -> None:
    field_map = {
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_slot": "slot",
    }
    for session_field, row_field in field_map.items():
        if _clean(getattr(upload_session_doc, session_field, None)):
            continue
        value = _clean(drive_file_row.get(row_field))
        if value:
            setattr(upload_session_doc, session_field, value)


def _binding_target_exists(upload_session_doc) -> bool:
    binding_doctype = _clean(getattr(upload_session_doc, "attached_doctype", None))
    binding_name = _clean(getattr(upload_session_doc, "attached_name", None))
    if not binding_doctype or not binding_name:
        return False

    exists = getattr(frappe.db, "exists", None)
    if not callable(exists):
        return True
    return bool(exists(binding_doctype, binding_name))


def _infer_binding_role(upload_session_doc, drive_file_row: dict[str, Any]) -> str | None:
    attached_doctype = _clean(
        getattr(upload_session_doc, "attached_doctype", None) or drive_file_row.get("attached_doctype")
    )
    owner_doctype = _clean(getattr(upload_session_doc, "owner_doctype", None) or drive_file_row.get("owner_doctype"))
    slot = _clean(getattr(upload_session_doc, "intended_slot", None) or drive_file_row.get("slot"))

    if attached_doctype == "Supporting Material":
        return "general_reference"
    if attached_doctype == "Org Communication":
        return "communication_attachment"
    if attached_doctype == "Task":
        return "task_resource"
    if owner_doctype == "Organization" and any(slot.startswith(prefix) for prefix in _ORGANIZATION_MEDIA_SLOT_PREFIXES):
        return "organization_media"
    return None


def _resolve_binding_role_for_row(upload_session_doc, drive_file_row: dict[str, Any]) -> str | None:
    try:
        binding_role = _resolve_binding_role(upload_session_doc)
    except Exception:
        binding_role = None
    return binding_role or _infer_binding_role(upload_session_doc, drive_file_row)


def _log_backfill_skip(*, drive_file_id: str, reason: str, detail: str | None = None) -> None:
    log_error = getattr(frappe, "log_error", None)
    if not callable(log_error):
        return

    payload = {"drive_file": drive_file_id, "reason": reason}
    if detail:
        payload["detail"] = detail
    log_error(frappe.as_json(payload, indent=2), "Drive Binding Backfill Skipped")


def _create_primary_binding(*, drive_file_id: str, file_id: str, upload_session_doc, binding_role: str) -> str | None:
    from ifitwala_drive.services.files.creation import _create_primary_binding as drive_create_primary_binding

    return drive_create_primary_binding(
        drive_file_id=drive_file_id,
        file_id=file_id,
        upload_session_doc=upload_session_doc,
        binding_role=binding_role,
    )


def execute():
    if not all(frappe.db.table_exists(doctype) for doctype in _REQUIRED_TABLES):
        return

    failures: list[tuple[str, str]] = []
    skipped = 0
    for row in _load_candidate_drive_files():
        drive_file_id = str(row.get("name") or "").strip()
        file_id = str(row.get("file") or "").strip()
        upload_session_id = str(row.get("source_upload_session") or "").strip()
        if not drive_file_id or not file_id or not upload_session_id:
            continue
        if _has_active_primary_binding(drive_file_id):
            continue

        try:
            upload_session_doc = frappe.get_doc("Drive Upload Session", upload_session_id)
            _hydrate_upload_session_context(upload_session_doc, row)
            binding_role = _resolve_binding_role_for_row(upload_session_doc, row)
            if not binding_role:
                _log_backfill_skip(drive_file_id=drive_file_id, reason="binding_role_unresolved")
                skipped += 1
                continue
            if not _binding_target_exists(upload_session_doc):
                _log_backfill_skip(
                    drive_file_id=drive_file_id,
                    reason="binding_target_missing",
                    detail="{} {}".format(
                        _clean(getattr(upload_session_doc, "attached_doctype", None)),
                        _clean(getattr(upload_session_doc, "attached_name", None)),
                    ).strip(),
                )
                skipped += 1
                continue
            _create_primary_binding(
                drive_file_id=drive_file_id,
                file_id=file_id,
                upload_session_doc=upload_session_doc,
                binding_role=binding_role,
            )
        except Exception:
            log_error = getattr(frappe, "log_error", None)
            get_traceback = getattr(frappe, "get_traceback", None)
            trace = get_traceback() if callable(get_traceback) else f"drive_binding_backfill_failed: {drive_file_id}"
            if callable(log_error):
                log_error(trace, "Drive Binding Backfill Failed")
            failures.append((drive_file_id, trace))

    if failures:
        sample = ", ".join(name for name, _error in failures[:5])
        remaining = max(0, len(failures) - 5)
        suffix = _(" (+{0} more)").format(remaining) if remaining else ""
        log_error = getattr(frappe, "log_error", None)
        if callable(log_error):
            log_error(
                _(
                    "Drive binding backfill encountered unexpected failures for authoritative Drive files: {sample}{suffix}. Skipped rows: {skipped}."
                ).format(sample=sample or _("unknown files"), suffix=suffix, skipped=skipped),
                "Drive Binding Backfill Summary",
            )
