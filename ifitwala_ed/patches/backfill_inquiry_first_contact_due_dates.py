from __future__ import annotations

import frappe

from ifitwala_ed.admission.admission_utils import set_inquiry_deadlines


def execute():
    if not frappe.db.table_exists("Inquiry"):
        return

    inquiry_rows = frappe.get_all(
        "Inquiry",
        filters={"first_contact_due_on": ["is", "not set"]},
        fields=["name", "submitted_at", "creation"],
        limit=100000,
    )

    for inquiry_row in inquiry_rows:
        _backfill_inquiry_first_contact_due_on(inquiry_row)


def _backfill_inquiry_first_contact_due_on(inquiry_row: dict) -> None:
    inquiry_name = str(inquiry_row.get("name") or "").strip()
    if not inquiry_name:
        return

    inquiry_doc = frappe.get_doc("Inquiry", inquiry_name)
    if getattr(inquiry_doc, "first_contact_due_on", None):
        return

    if not getattr(inquiry_doc, "submitted_at", None) and inquiry_row.get("creation"):
        inquiry_doc.submitted_at = inquiry_row.get("creation")

    set_inquiry_deadlines(inquiry_doc)

    if getattr(inquiry_doc, "first_contact_due_on", None):
        frappe.db.set_value(
            "Inquiry",
            inquiry_name,
            "first_contact_due_on",
            inquiry_doc.first_contact_due_on,
            update_modified=False,
        )
