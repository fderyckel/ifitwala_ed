# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import os
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_files_path
from pathlib import Path

class FileManagement(Document):

    @frappe.whitelist()
    def run_dry_run(self):
        """Triggered by the native Button field (Dry Run)."""
        self._file_management_executor(dry_run=True)

    def _file_management_executor(self, dry_run=True):
        moved_files = []
        deleted_thumbnails = []
        skipped_files = []

        # --- Step 1: Move misfiled attached images ---
        for row in self.managed_doctypes:
            if not row.move_image: 
                continue

            if not row.active:
                continue

            target_folder = row.doctype_link.lower()

            files = frappe.get_all(
                "File",
                fields=["name", "file_url", "attached_to_doctype", "attached_to_name", "folder", "file_name"],
                filters={
                    "attached_to_doctype": row.doctype_link,
                    "is_folder": 0,
                    "is_private": 0
                }
            )

            for f in files:
                if not f.file_url:
                    continue
                if f.folder and f.folder.lower() == f"home/{target_folder}":
                    continue
                if any(f.file_name.startswith(prefix) for prefix in ["small_", "medium_", "large_"]):
                    continue

                old_full_path = frappe.utils.get_site_path("public", f.file_url.lstrip("/"))
                if not os.path.exists(old_full_path):
                    skipped_files.append(f"Missing on disk: {f.file_url}")
                    continue

                folder_path = frappe.utils.get_site_path("public", "files", target_folder)
                os.makedirs(folder_path, exist_ok=True)

                new_relative_path = f"files/{target_folder}/{f.file_name}"
                new_full_path = frappe.utils.get_site_path("public", new_relative_path)

                if not dry_run:
                    os.rename(old_full_path, new_full_path)
                    frappe.db.set_value("File", f.name, {
                        "file_url": f"/{new_relative_path}",
                        "folder": f"Home/{target_folder}"
                    })

                    if f.attached_to_doctype and f.attached_to_name and f.attached_to_field:
                        try:
                            frappe.db.set_value(
                                f.attached_to_doctype,
                                f.attached_to_name,
                                f.attached_to_field,
                                f"/{new_relative_path}"
                            )
                        except Exception as e:
                            frappe.log_error(f"Error updating linked document {f.attached_to_doctype} {f.attached_to_name}: {e}", "Linked Doc Update Error")

        # --- Step 2: Clean orphaned thumbnails ---
        public_files_path = Path(get_files_path())

        for file_path in public_files_path.glob("*_*.*"):
            if file_path.name.startswith(("small_", "medium_", "large_")):
                gallery_match = public_files_path / "gallery_resized" / file_path.name
                if gallery_match.exists():
                    continue

                if not dry_run:
                    try:
                        file_path.unlink()
                        file_doc_name = frappe.db.get_value(
                            "File", {"file_url": f"/files/{file_path.name}"}, "name"
                        )
                        if file_doc_name:
                            frappe.delete_doc("File", file_doc_name, force=1)
                    except Exception as e:
                        frappe.log_error(f"Error deleting thumbnail {file_path.name}: {e}", "Thumbnail Deletion Error")

                deleted_thumbnails.append(file_path.name)

        # --- Step 3: Save admin notes (ALWAYS now) ---
        summary = []

        if dry_run:
            summary.append(f"We found {len(moved_files)} file(s) to be moved:")
            for f in moved_files:
                summary.append(f"  - {f}")

            summary.append(f"\nWe found {len(deleted_thumbnails)} orphaned thumbnail(s) to be deleted:")
            for f in deleted_thumbnails:
                summary.append(f"  - {f}")

            summary.append(f"\nWe found {len(skipped_files)} missing file(s) on disk:")
            for f in skipped_files:
                summary.append(f"  - {f}")
        else:
            summary.append(f"Moved {len(moved_files)} file(s).")
            summary.append("")
            summary.append(f"Deleted {len(deleted_thumbnails)} orphaned thumbnail(s).")
            summary.append("")
            summary.append(f"Skipped {len(skipped_files)} missing file(s).")

        self.admin_notes = "\n".join(summary)
        self.last_action_date = frappe.utils.now_datetime()

        self.save(ignore_permissions=True)

        return {
            "moved_files": moved_files,
            "deleted_thumbnails": deleted_thumbnails,
            "skipped_files": skipped_files,
            "dry_run": dry_run,
            "summary": summary,
        }

@frappe.whitelist()
def run_execute():
    fm = frappe.get_single("File Management")
    return fm._file_management_executor(dry_run=False)