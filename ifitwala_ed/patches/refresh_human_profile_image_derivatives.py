from __future__ import annotations

import frappe
from ifitwala_drive.services.files.derivatives import (
    mark_version_derivatives_stale,
    preview_plan_for_drive_file,
    run_preview_job,
    sync_preview_pipeline_for_current_version,
)
from ifitwala_drive.services.files.versions import ensure_current_drive_file_version

_CURRENT_PROFILE_IMAGE_STATUSES = ("active", "processing", "blocked")
_PROFILE_IMAGE_SUBJECT_TYPES = ("Employee", "Student", "Guardian", "Student Applicant")
_APPLICANT_PROFILE_IMAGE_SLOT = "profile_image"
_GUARDIAN_PROFILE_IMAGE_SLOT_PREFIX = "guardian_profile_image__"


def _is_human_profile_image_slot(*, subject_type: str | None, slot: str | None) -> bool:
    resolved_subject_type = str(subject_type or "").strip()
    resolved_slot = str(slot or "").strip()
    if resolved_subject_type != "Student Applicant":
        return resolved_slot == _APPLICANT_PROFILE_IMAGE_SLOT
    return resolved_slot == _APPLICANT_PROFILE_IMAGE_SLOT or resolved_slot.startswith(
        _GUARDIAN_PROFILE_IMAGE_SLOT_PREFIX
    )


def execute() -> None:
    if not frappe.db.table_exists("Drive File") or not frappe.db.table_exists("Drive File Version"):
        return

    rows = frappe.get_all(
        "Drive File",
        filters={
            "primary_subject_type": ["in", list(_PROFILE_IMAGE_SUBJECT_TYPES)],
            "status": ["in", list(_CURRENT_PROFILE_IMAGE_STATUSES)],
        },
        fields=["name", "primary_subject_type", "slot"],
        limit=0,
    )

    for row in rows:
        drive_file_id = str(row.get("name") or "").strip()
        if not drive_file_id or not _is_human_profile_image_slot(
            subject_type=row.get("primary_subject_type"),
            slot=row.get("slot"),
        ):
            continue

        try:
            drive_file_doc = frappe.get_doc("Drive File", drive_file_id)
            current_version = ensure_current_drive_file_version(drive_file_doc=drive_file_doc)
            current_version = str(current_version or getattr(drive_file_doc, "current_version", "") or "").strip()
            if not current_version:
                continue
            drive_file_doc.current_version = current_version

            mime_type = frappe.db.get_value("Drive File Version", current_version, "mime_type")
            if not mime_type:
                continue

            plan = preview_plan_for_drive_file(drive_file_doc, mime_type)
            if not plan.get("supported") or not plan.get("derivative_roles"):
                continue

            mark_version_derivatives_stale(
                drive_file_id=drive_file_doc.name,
                drive_file_version_id=current_version,
            )
            result = sync_preview_pipeline_for_current_version(
                drive_file_doc=drive_file_doc,
                mime_type=mime_type,
            )
            job_id = str((result or {}).get("drive_processing_job_id") or "").strip()
            if job_id:
                run_preview_job(drive_processing_job_id=job_id)
        except Exception:
            frappe.log_error(
                frappe.as_json(
                    {
                        "error": "human_profile_image_derivative_refresh_failed",
                        "drive_file": drive_file_id,
                    },
                    indent=2,
                ),
                "Human Profile Image Derivative Refresh Failed",
            )
