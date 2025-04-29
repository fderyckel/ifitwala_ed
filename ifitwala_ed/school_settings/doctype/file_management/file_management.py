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
            if not row.active or not row.move_attached_images:
                continue

            target_folder = row.doctype_link.lower()
            expected_folder = f"Home/{target_folder}"

            # Ensure File folder exists (as File Doctype folder)
            if not frappe.db.exists("File", {"file_name": target_folder, "folder": "Home"}):
                frappe.get_doc({
                    "doctype": "File",
                    "file_name": target_folder,
                    "is_folder": 1,
                    "folder": "Home"
                }).insert(ignore_permissions=True)

            files = frappe.get_all(
                "File",
                fields=["name"],
                filters={
                    "attached_to_doctype": row.doctype_link,
                    "is_folder": 0,
                    "is_private": 0
                }
            )

            for file_meta in files:
                file_doc = frappe.get_doc("File", file_meta.name)
                current_folder = (file_doc.folder or "").lower()
                if current_folder == expected_folder.lower():
                    continue
                if not file_doc.file_url:
                    continue
                if any(file_doc.file_name.startswith(prefix) for prefix in ["small_", "medium_", "large_"]):
                    continue

                old_full_path = os.path.join(get_files_path(), os.path.basename(file_doc.file_url))
                if not os.path.exists(old_full_path):
                    skipped_files.append(f"Missing on disk: {file_doc.file_url}")
                    continue

                # Destination
                folder_path = os.path.join(get_files_path(), target_folder)
                os.makedirs(folder_path, exist_ok=True)

                new_file_path = os.path.join(folder_path, file_doc.file_name)
                new_relative_path = f"files/{target_folder}/{file_doc.file_name}"

                moved_files.append(file_doc.file_name)

                if not dry_run:
                    os.rename(old_full_path, new_file_path)
                    file_doc.file_url = f"/{new_relative_path}"
                    file_doc.folder = expected_folder
                    file_doc.is_private = 0
                    file_doc.save(ignore_permissions=True)

                    if file_doc.attached_to_doctype and file_doc.attached_to_name and file_doc.attached_to_field:
                        try:
                            frappe.db.set_value(
                                file_doc.attached_to_doctype,
                                file_doc.attached_to_name,
                                file_doc.attached_to_field,
                                f"/{new_relative_path}"
                            )
                        except Exception as e:
                            frappe.log_error(
                                f"Error updating {file_doc.attached_to_doctype} {file_doc.attached_to_name}: {e}",
                                "Linked Doc Update Error"
                            )

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

        # --- Step 3: Save admin notes ---
        summary = []

        if dry_run:
            summary.append(f" 🗂  We found {len(moved_files)} file(s) to be moved:")
            for f in moved_files:
                summary.append(f"  - {f}")

            summary.append(f"\n 🖼️  We found {len(deleted_thumbnails)} optimized copies to be deleted:")
            for f in deleted_thumbnails:
                summary.append(f"  - {f}")

            summary.append(f"\n ⚠️  We found {len(skipped_files)} missing file(s) on disk:")
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
    def clear_notes_and_date(self):
        """Clear admin_notes and last_action_date."""
        self.admin_notes = ""
        self.last_action_date = None
        self.save(ignore_permissions=True)


@frappe.whitelist()
def run_execute():
    fm = frappe.get_single("File Management")
    return fm._file_management_executor(dry_run=False)