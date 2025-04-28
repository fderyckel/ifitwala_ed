# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/file_management/file_management.py

import frappe
import os
from frappe import _
from frappe.utils import get_files_path
from pathlib import Path

@frappe.whitelist()
def run_dry_run():
    """Dry run of File Management maintenance."""
    return _file_management_executor(dry_run=True)

@frappe.whitelist()
def run_execute():
    """Real execution of File Management maintenance."""
    return _file_management_executor(dry_run=False)

def _file_management_executor(dry_run=True):
    moved_files = []
    deleted_thumbnails = []
    skipped_files = []

    file_management_settings = frappe.get_single("File Management")

    # --- Step 1: Move misfiled attached images ---
    for row in file_management_settings.managed_doctypes:
        if not row.active:
            continue

        target_folder = row.doctype_link.lower()

        files = frappe.get_all("File", fields=["name", "file_url", "attached_to_doctype", "attached_to_name", "folder", "file_name"],
            filters={
                "attached_to_doctype": row.doctype_link,
                "is_folder": 0,
                "is_private": 0
            })

        for f in files:
            if not f.file_url:
                continue

            # Skip files that are already correctly moved
            if f.folder and f.folder.lower() == f"home/{target_folder}":
                continue

            # Skip Frappe generated thumbnails (small_, medium_, large_) in filename
            if any(f.file_name.startswith(prefix) for prefix in ["small_", "medium_", "large_"]):
                continue

            # Check if file physically exists
            old_full_path = frappe.utils.get_site_path("public", f.file_url.lstrip("/"))
            if not os.path.exists(old_full_path):
                skipped_files.append(f"Missing on disk: {f.file_url}")
                continue

            # Ensure folder exists
            folder_path = frappe.utils.get_site_path("public", "files", target_folder)
            os.makedirs(folder_path, exist_ok=True)

            # New relative path
            new_relative_path = f"files/{target_folder}/{f.file_name}"
            new_full_path = frappe.utils.get_site_path("public", new_relative_path)

            if not dry_run:
                os.rename(old_full_path, new_full_path)
                frappe.db.set_value("File", f.name, {
                    "file_url": f"/{new_relative_path}",
                    "folder": f"Home/{target_folder}"
                }, update_modified=False)

            moved_files.append(f.file_name)

    # --- Step 2: Clean orphaned small_, medium_, large_ thumbnails ---
    public_files_path = Path(get_files_path())

    for file_path in public_files_path.glob("*_*.*"):
        if file_path.name.startswith(("small_", "medium_", "large_")):
            # Check if equivalent exists in gallery_resized
            gallery_match = public_files_path / "gallery_resized" / file_path.name
            if gallery_match.exists():
                continue  # OK, file is protected

            if not dry_run:
                try:
                    file_path.unlink()
                    frappe.db.delete("File", {"file_url": f"/files/{file_path.name}"})
                except Exception as e:
                    frappe.log_error(f"Error deleting thumbnail {file_path.name}: {e}", "Thumbnail Deletion Error")

            deleted_thumbnails.append(file_path.name)

    # --- Step 3: Save admin notes ---
    summary = []
    summary.append(f"Moved {len(moved_files)} file(s).")
    summary.append(f"Deleted {len(deleted_thumbnails)} orphaned thumbnail(s).")
    summary.append(f"Skipped {len(skipped_files)} missing file(s).")

    if not dry_run:
        file_management_settings.admin_notes = "\n".join(summary)
        file_management_settings.last_action_date = frappe.utils.now_datetime()
        file_management_settings.save(ignore_permissions=True)

    return {
        "moved_files": moved_files,
        "deleted_thumbnails": deleted_thumbnails,
        "skipped_files": skipped_files,
        "dry_run": dry_run,
        "summary": summary,
    }

