# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/picture_management/picture_management.py

"""File Management single DocType

Controls maintenance actions on attachments and generated thumbnails for each
managed Doctype.  Each child-table row exposes three independent switches:

* **active**  - master enable. If unchecked the row is ignored entirely.
* **move_attached_images** - move misplaced *images* into Home/<doctype>/.
* **clean_orphan_thumbnails** - delete unused hero_/medium_/card_/thumb_ files.

A dry-run button simulates the operation without changing disk/database and
writes a full summary to *admin_notes* either way.
"""

from __future__ import annotations

import os
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import get_files_path


class PictureManagement(Document):
    # ----------------------------------------------------------------------
    # Public trigger helpers
    # ----------------------------------------------------------------------
    @frappe.whitelist()
    def run_dry_run(self):
        """Clicked from the button on the DocType - no writes."""
        return self._file_management_executor(dry_run=True)

    @frappe.whitelist()
    def clear_notes_and_date(self):
        """Utility: clear admin notes & date."""
        self.admin_notes = ""
        self.last_action_date = None
        self.save(ignore_permissions=True)

    # ----------------------------------------------------------------------
    # Internals – core helpers
    # ----------------------------------------------------------------------
    def _move_images(self, row, dry_run: bool, moved: list[str], skipped: list[str]):
        """Relocate mis-filed *images* for one Managed-Doctype row."""
        target_folder_name = row.doctype_link.lower()
        expected_folder_path = f"Home/{target_folder_name}"

        # Ensure target folder exists
        if not frappe.db.exists(
            "File",
            {"file_name": target_folder_name, "is_folder": 1, "folder": "Home"},
        ):
            frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": target_folder_name,
                    "is_folder": 1,
                    "folder": "Home",
                }
            ).insert(ignore_permissions=True)

        # Collect files linked to this Doctype
        files = frappe.get_all(
            "File",
            fields=[
                "name",
                "file_url",
                "file_name",
                "folder",
                "attached_to_doctype",
                "attached_to_name",
                "attached_to_field",
            ],
            filters={
                "attached_to_doctype": row.doctype_link,
                "is_folder": 0,
                "is_private": 0,
            },
        )

        for f in files:
            if not f.file_url:
                continue

            # Skip generated thumbnails
            if f.file_name.startswith(("hero_", "medium_", "card_", "thumb_")):
                continue

            old_full_path = frappe.utils.get_site_path("public", f.file_url.lstrip("/"))
            if not os.path.exists(old_full_path):
                skipped.append(f"Missing on disk: {f.file_url}")
                continue

            # Already in correct folder?
            file_folder_doc = (
                frappe.db.get_value("File", f.folder, ["file_name", "folder"], as_dict=True)
                if f.folder
                else None
            )
            if (
                file_folder_doc
                and file_folder_doc.file_name.lower() == target_folder_name
                and file_folder_doc.folder == "Home"
            ):
                continue

            # Prepare new location
            new_relative_path = f"files/{target_folder_name}/{f.file_name}"
            new_full_path = frappe.utils.get_site_path("public", new_relative_path)

            moved.append(f.file_name)
            if dry_run:
                continue

            # Execute move
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            os.rename(old_full_path, new_full_path)

            old_url = f.file_url
            frappe.db.set_value(
                "File",
                f.name,
                {"file_url": f"/{new_relative_path}", "folder": expected_folder_path},
            )

            # Update duplicates that reference same physical file
            duplicates = frappe.get_all(
                "File",
                filters={"file_url": old_url, "name": ["!=", f.name], "is_folder": 0},
                fields=["name", "attached_to_doctype", "attached_to_name", "attached_to_field"],
            )
            for dup in duplicates:
                frappe.db.set_value(
                    "File", dup.name, "file_url", f"/{new_relative_path}", update_modified=False
                )
                if dup.attached_to_doctype and dup.attached_to_field:
                    frappe.db.set_value(
                        dup.attached_to_doctype,
                        dup.attached_to_name,
                        dup.attached_to_field,
                        f"/{new_relative_path}",
                        update_modified=False,
                    )

            # Patch original linked DocField
            if f.attached_to_doctype and f.attached_to_name and f.attached_to_field:
                try:
                    frappe.db.set_value(
                        f.attached_to_doctype,
                        f.attached_to_name,
                        f.attached_to_field,
                        f"/{new_relative_path}",
                    )
                except Exception as e:
                    frappe.log_error(
                        f"Error updating linked {f.attached_to_doctype} {f.attached_to_name}: {e}",
                        "Linked Doc Update Error",
                    )

    def _clean_thumbnails(self, dry_run: bool) -> list[str]:
        """Delete orphaned hero_/medium_/card_/thumb_ images. Return their names."""
        deleted: list[str] = []
        base_path = Path(get_files_path())

        for fp in base_path.glob("*_*.*"):
            if not fp.name.startswith(("hero_", "medium_", "card_", "thumb_")):
                continue

            if (base_path / "gallery_resized" / fp.name).exists():
                continue  # keep optimised copies

            if not dry_run:
                try:
                    fp.unlink()
                    docname = frappe.db.get_value("File", {"file_url": f"/files/{fp.name}"}, "name")
                    if docname:
                        frappe.delete_doc("File", docname, force=1)
                except Exception as e:
                    frappe.log_error(f"Error deleting thumbnail {fp.name}: {e}", "Thumbnail Deletion Error")
            deleted.append(fp.name)

        return deleted

    def _build_summary(self, moved: list[str], deleted: list[str], skipped: list[str], dry_run: bool) -> str:
        """Compose human-readable admin_notes text."""
        lines: list[str] = []
        if dry_run:
            lines.append(f" 🗂  We found {len(moved)} file(s) to be moved:")
            lines.extend([f"  - {f}" for f in moved])
            lines.append(f"\n 🖼️  We found {len(deleted)} optimized copies to be deleted:")
            lines.extend([f"  - {f}" for f in deleted])
            lines.append(f"\n ⚠️  We found {len(skipped)} missing file(s) on disk:")
            lines.extend([f"  - {f}" for f in skipped])
        else:
            lines.append(f"Moved {len(moved)} file(s).\n")
            lines.append(f"Deleted {len(deleted)} orphaned thumbnail(s).\n")
            lines.append(f"Skipped {len(skipped)} missing file(s).")
        return "\n".join(lines)

    # ----------------------------------------------------------------------
    # Main executor
    # ----------------------------------------------------------------------
    def _file_management_executor(self, *, dry_run: bool = True):
        moved_files: list[str] = []
        skipped_files: list[str] = []
        deleted_thumbnails: list[str] = []
        run_thumb_cleanup = False

        # Step 1 – child rows actions
        for row in self.managed_doctypes:
            if not row.active:
                continue
            if row.move_attached_images:
                self._move_images(row, dry_run, moved_files, skipped_files)
            if row.clean_orphan_thumbnails:
                run_thumb_cleanup = True

        # Step 2 – global thumbnail cleanup (once)
        if run_thumb_cleanup:
            deleted_thumbnails = self._clean_thumbnails(dry_run)

        # Step 3 – summary & persistence
        summary_text = self._build_summary(moved_files, deleted_thumbnails, skipped_files, dry_run)
        self.admin_notes = summary_text
        self.last_action_date = frappe.utils.now_datetime()
        self.save(ignore_permissions=True)

        return {
            "moved_files": moved_files,
            "deleted_thumbnails": deleted_thumbnails,
            "skipped_files": skipped_files,
            "dry_run": dry_run,
            "summary": summary_text.splitlines(),
        }


# ----------------------------------------------------------------------
# Convenience wrapper for Scheduler / manual execute
# ----------------------------------------------------------------------
@frappe.whitelist()
def run_execute():
    """Server-side shortcut to perform the real operation (dry_run=False)."""
    fm = frappe.get_single("Picture Management")
    return fm._file_management_executor(dry_run=False)
