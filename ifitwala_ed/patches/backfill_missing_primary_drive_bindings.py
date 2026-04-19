from __future__ import annotations

from typing import Any

import frappe
from frappe import _

_REQUIRED_TABLES = {"Drive File", "Drive Upload Session", "Drive Binding"}
_BINDING_ELIGIBLE_STATUSES = {"active", "blocked", "processing"}


def _load_candidate_drive_files() -> list[dict[str, Any]]:
    return (
        frappe.get_all(
            "Drive File",
            filters={"status": ["in", sorted(_BINDING_ELIGIBLE_STATUSES)]},
            fields=["name", "file", "source_upload_session", "status"],
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
            binding_role = _resolve_binding_role(upload_session_doc)
            if not binding_role:
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
        frappe.throw(
            _(
                "Drive binding backfill failed for authoritative Drive files: {sample}{suffix}. See Error Log for details."
            ).format(sample=sample or _("unknown files"), suffix=suffix)
        )
