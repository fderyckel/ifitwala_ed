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

            target_folder_name = row.doctype_link.lower()
            expected_folder_path = f"Home/{target_folder_name}"

            # ⚡ Step 1.1: Ensure target folder exists as a File Doc
            folder_doc = frappe.db.exists("File", {"file_name": target_folder_name, "is_folder": 1, "folder": "Home"})
            if not folder_doc:
                frappe.get_doc({
                    "doctype": "File",
                    "file_name": target_folder_name,
                    "is_folder": 1,
                    "folder": "Home"
                }).insert(ignore_permissions=True)

            # ⚡ Step 1.2: Now fetch all File docs that should be in this folder
            files = frappe.get_all(
                "File",
                fields=["name", "file_url", "file_name", "folder", "attached_to_doctype", "attached_to_name", "attached_to_field"],
                filters={
                    "attached_to_doctype": row.doctype_link,
                    "is_folder": 0,
                    "is_private": 0,
                }
            )

            for f in files:
                if not f.file_url:
                    continue

                # ⚡ Ignore system thumbnails (small_, medium_, large_)
                if any(f.file_name.startswith(prefix) for prefix in ["small_", "medium_", "large_"]):
                    continue

                old_full_path = frappe.utils.get_site_path("public", f.file_url.lstrip("/"))
                if not os.path.exists(old_full_path):
                    skipped_files.append(f"Missing on disk: {f.file_url}")
                    continue

                # ⚡ Check if already inside the correct folder
                file_folder_doc = frappe.db.get_value("File", f.folder, ["file_name", "folder"], as_dict=True) if f.folder else None

                if file_folder_doc:
                    if file_folder_doc.get("file_name", "").lower() == target_folder_name and file_folder_doc.get("folder", "") == "Home":
                        continue  # Already in correct folder!

                # ⚡ Step 1.3: Prepare move
                new_relative_path = f"files/{target_folder_name}/{f.file_name}"
                new_full_path = frappe.utils.get_site_path("public", new_relative_path)

                # ✏️ Track file for admin notes
                moved_files.append(f.file_name)

                if not dry_run:
                    # ⚡ Move physical file
                    os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
                    os.rename(old_full_path, new_full_path)

                    # ⚡ Update File Doc
                    frappe.db.set_value("File", f.name, {
                        "file_url": f"/{new_relative_path}",
                        "folder": expected_folder_path,
                    })

                    # 🚀 NEW —— propagate the new path to every *other* File row
                    duplicates = frappe.get_all(
                        "File",
                        filters={
                            "file_url": f.file_url,           # ← OLD url (still in var f at this point)
                            "name":     ["!=", f.name],       # skip the one we just updated
                            "is_folder": 0
                        },
                        fields=["name", "attached_to_doctype",
                                "attached_to_name", "attached_to_field"]
                    )

                    for dup in duplicates:
                        frappe.db.set_value(
                            "File", dup.name,
                            {
                                "file_url": f"/{new_relative_path}",
                                "folder":   expected_folder_path,
                            },
                            update_modified=False,
                        )

                        # also update the field on the linked document so the UI shows the right url
                        if dup.attached_to_doctype and dup.attached_to_field:
                            frappe.db.set_value(
                                dup.attached_to_doctype,
                                dup.attached_to_name,
                                dup.attached_to_field,
                                f"/{new_relative_path}",
                                update_modified=False,
                            )


                    # ⚡ Update attached_to_document field if needed
                    if f.attached_to_doctype and f.attached_to_name and f.attached_to_field:
                        try:
                            frappe.db.set_value(
                                f.attached_to_doctype,
                                f.attached_to_name,
                                f.attached_to_field,
                                f"/{new_relative_path}"
                            )
                        except Exception as e:
                            frappe.log_error(
                                f"Error updating linked {f.attached_to_doctype} {f.attached_to_name}: {e}",
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