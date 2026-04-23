from __future__ import annotations

import frappe
from ifitwala_drive.services.files.derivatives import (
    preview_plan_for_drive_file,
    resolve_ready_preview_derivative_state,
    run_preview_job,
    sync_preview_pipeline_for_current_version,
)
from ifitwala_drive.services.files.versions import ensure_current_drive_file_version

from ifitwala_ed.patches import repair_governed_profile_images

_PROFILE_IMAGE_CURRENT_FILE_STATUSES = ("active", "processing", "blocked")
_PROFILE_IMAGE_SUBJECT_TYPES = ("Employee", "Student", "Guardian")


def _all_profile_preview_roles_ready(*, drive_file_doc, derivative_roles: list[str]) -> bool:
    return all(
        resolve_ready_preview_derivative_state(
            drive_file_doc=drive_file_doc,
            derivative_role=derivative_role,
        ).get("state")
        == "ready"
        for derivative_role in derivative_roles
    )


def _materialize_current_profile_image_derivatives() -> None:
    if not frappe.db.table_exists("Drive File") or not frappe.db.table_exists("Drive File Version"):
        return

    rows = frappe.get_all(
        "Drive File",
        filters={
            "slot": "profile_image",
            "primary_subject_type": ["in", list(_PROFILE_IMAGE_SUBJECT_TYPES)],
            "status": ["in", list(_PROFILE_IMAGE_CURRENT_FILE_STATUSES)],
        },
        fields=["name"],
        limit=0,
    )

    for row in rows:
        drive_file_id = str(row.get("name") or "").strip()
        if not drive_file_id:
            continue

        try:
            drive_file_doc = frappe.get_doc("Drive File", drive_file_id)
            current_version = ensure_current_drive_file_version(drive_file_doc=drive_file_doc)
            if current_version:
                drive_file_doc.current_version = current_version
            current_version = str(current_version or "").strip()
            if not current_version:
                continue

            mime_type = frappe.db.get_value("Drive File Version", current_version, "mime_type")
            if not mime_type:
                continue

            plan = preview_plan_for_drive_file(drive_file_doc, mime_type)
            derivative_roles = [
                str(role or "").strip() for role in (plan.get("derivative_roles") or []) if str(role or "").strip()
            ]
            if not plan.get("supported") or not derivative_roles:
                continue

            if _all_profile_preview_roles_ready(
                drive_file_doc=drive_file_doc,
                derivative_roles=derivative_roles,
            ):
                continue

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
                        "error": "profile_image_derivative_materialization_failed",
                        "drive_file": drive_file_id,
                    },
                    indent=2,
                ),
                "Profile Image Derivative Materialization Failed",
            )


def execute() -> None:
    repair_governed_profile_images.execute()
    _materialize_current_profile_image_derivatives()
