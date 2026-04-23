from __future__ import annotations

import frappe

from ifitwala_ed.integrations.drive.admissions import _build_guardian_profile_image_slot
from ifitwala_ed.integrations.drive.authority import get_current_drive_file_for_slot
from ifitwala_ed.patches.normalize_profile_image_privacy import _compute_private_file_url

_ADMISSIONS_SUBJECT_TYPE = "Student Applicant"
_APPLICANT_PROFILE_IMAGE_SLOT = "profile_image"
_GUARDIAN_PROFILE_IMAGE_SLOT_PREFIX = "guardian_profile_image__"
_CURRENT_PROFILE_IMAGE_STATUSES = ("active", "processing", "blocked")


def _is_admissions_profile_image_slot(slot: str | None) -> bool:
    resolved_slot = str(slot or "").strip()
    return resolved_slot == _APPLICANT_PROFILE_IMAGE_SLOT or resolved_slot.startswith(
        _GUARDIAN_PROFILE_IMAGE_SLOT_PREFIX
    )


def _normalize_drive_file_rows() -> None:
    if not frappe.db.table_exists("Drive File"):
        return

    rows = frappe.get_all(
        "Drive File",
        filters={"primary_subject_type": _ADMISSIONS_SUBJECT_TYPE},
        fields=[
            "name",
            "slot",
            "file",
            "source_upload_session",
            "storage_backend",
            "storage_object_key",
        ],
        limit=0,
    )

    for row in rows:
        if not _is_admissions_profile_image_slot(row.get("slot")):
            continue

        drive_file_name = str(row.get("name") or "").strip()
        file_name = str(row.get("file") or "").strip()
        upload_session_name = str(row.get("source_upload_session") or "").strip()
        if not drive_file_name:
            continue

        frappe.db.set_value("Drive File", drive_file_name, "is_private", 1, update_modified=False)

        if file_name and frappe.db.exists("File", file_name):
            values: dict[str, object] = {"is_private": 1}
            private_file_url = _compute_private_file_url(
                storage_backend=row.get("storage_backend"),
                object_key=row.get("storage_object_key"),
            )
            if private_file_url:
                values["file_url"] = private_file_url
            frappe.db.set_value("File", file_name, values, update_modified=False)

        if upload_session_name and frappe.db.exists("Drive Upload Session", upload_session_name):
            frappe.db.set_value("Drive Upload Session", upload_session_name, "is_private", 1, update_modified=False)


def _sync_current_profile_fields() -> None:
    if not frappe.db.table_exists("Drive File"):
        return

    applicant_rows = frappe.get_all("Student Applicant", fields=["name"], limit=0)
    for row in applicant_rows:
        applicant_name = str(row.get("name") or "").strip()
        if not applicant_name:
            continue

        drive_file = get_current_drive_file_for_slot(
            primary_subject_type=_ADMISSIONS_SUBJECT_TYPE,
            primary_subject_id=applicant_name,
            slot=_APPLICANT_PROFILE_IMAGE_SLOT,
            attached_doctype="Student Applicant",
            attached_name=applicant_name,
            fields=["file"],
            statuses=_CURRENT_PROFILE_IMAGE_STATUSES,
        )
        file_name = str((drive_file or {}).get("file") or "").strip()
        if not file_name or not frappe.db.exists("File", file_name):
            continue

        file_url = str(frappe.db.get_value("File", file_name, "file_url") or "").strip()
        if file_url:
            frappe.db.set_value(
                "Student Applicant",
                applicant_name,
                "applicant_image",
                file_url,
                update_modified=False,
            )

    guardian_rows = frappe.get_all("Student Applicant Guardian", fields=["name", "parent"], limit=0)
    for row in guardian_rows:
        guardian_row_name = str(row.get("name") or "").strip()
        applicant_name = str(row.get("parent") or "").strip()
        if not guardian_row_name or not applicant_name:
            continue

        drive_file = get_current_drive_file_for_slot(
            primary_subject_type=_ADMISSIONS_SUBJECT_TYPE,
            primary_subject_id=applicant_name,
            slot=_build_guardian_profile_image_slot(guardian_row_name),
            attached_doctype="Student Applicant Guardian",
            attached_name=guardian_row_name,
            fields=["file"],
            statuses=_CURRENT_PROFILE_IMAGE_STATUSES,
        )
        file_name = str((drive_file or {}).get("file") or "").strip()
        if not file_name or not frappe.db.exists("File", file_name):
            continue

        file_url = str(frappe.db.get_value("File", file_name, "file_url") or "").strip()
        if file_url:
            frappe.db.set_value(
                "Student Applicant Guardian",
                guardian_row_name,
                "guardian_image",
                file_url,
                update_modified=False,
            )


def execute() -> None:
    _normalize_drive_file_rows()
    _sync_current_profile_fields()
