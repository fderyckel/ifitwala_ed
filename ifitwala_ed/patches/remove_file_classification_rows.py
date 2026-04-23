from __future__ import annotations

import frappe
from frappe import _


def _list_classification_rows() -> list[dict]:
    return (
        frappe.get_all(
            "File Classification",
            fields=["name", "file"],
            limit=100000,
        )
        or []
    )


def _find_missing_drive_rows(rows: list[dict]) -> list[dict]:
    missing: list[dict] = []
    for row in rows:
        file_name = str(row.get("file") or "").strip()
        if not file_name or not frappe.db.exists("Drive File", {"file": file_name}):
            missing.append(row)
    return missing


def execute():
    if not frappe.db.table_exists("File Classification"):
        return
    if not frappe.db.table_exists("Drive File"):
        frappe.throw(_("Cannot remove File Classification rows before Drive File exists."))

    rows = _list_classification_rows()
    if not rows:
        return

    missing_drive_rows = _find_missing_drive_rows(rows)
    if missing_drive_rows:
        sample = ", ".join(str(row.get("file") or row.get("name") or "").strip() for row in missing_drive_rows[:5])
        remaining = max(0, len(missing_drive_rows) - 5)
        suffix = _(" (+{0} more)").format(remaining) if remaining else ""
        frappe.throw(
            _(
                "Cannot remove File Classification rows before Drive authority exists for every governed file. Missing Drive File coverage for: {sample}{suffix}"
            ).format(sample=sample or _("unknown files"), suffix=suffix)
        )

    classification_names = [str(row.get("name") or "").strip() for row in rows if str(row.get("name") or "").strip()]
    if not classification_names:
        return

    if frappe.db.table_exists("File Classification Subject"):
        frappe.db.delete(
            "File Classification Subject",
            {"parenttype": "File Classification", "parent": ["in", classification_names]},
        )

    frappe.db.delete("File Classification", {"name": ["in", classification_names]})
