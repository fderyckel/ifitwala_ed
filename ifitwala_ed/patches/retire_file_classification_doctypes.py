from __future__ import annotations

import frappe
from frappe import _

_LEGACY_DOCTYPES = (
    "File Classification Subject",
    "File Classification",
)


def execute():
    if frappe.db.table_exists("File Classification") and frappe.db.count("File Classification"):
        frappe.throw(_("Cannot retire File Classification DocTypes before all classification rows are removed."))

    if frappe.db.table_exists("File Classification Subject"):
        remaining_rows = frappe.get_all(
            "File Classification Subject",
            filters={"parenttype": ["!=", "File Classification"]},
            fields=["parenttype"],
            limit=20,
        )
        if remaining_rows:
            parenttypes = ", ".join(sorted({row.get("parenttype") or "Unknown" for row in remaining_rows}))
            frappe.throw(
                _(
                    "Cannot retire File Classification DocTypes before non-classification child rows are migrated. Remaining parenttypes: {0}"
                ).format(parenttypes)
            )

    for doctype in _LEGACY_DOCTYPES:
        if frappe.db.exists("DocType", doctype):
            frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
