# ifitwala_ed/patches/setup/p02_drop_communication_interaction_entry_legacy_link.py

from __future__ import annotations

import frappe

ENTRY_DOCTYPE = "Communication Interaction Entry"
ENTRY_TABLE = "tabCommunication Interaction Entry"
ENTRY_LINK_FIELD = "communication_interaction"


def _delete_legacy_docfield_rows() -> int:
    if not frappe.db.table_exists("DocField"):
        return 0

    docfield_names = frappe.get_all(
        "DocField",
        filters={"parent": ENTRY_DOCTYPE, "fieldname": ENTRY_LINK_FIELD},
        pluck="name",
    )
    for docfield_name in docfield_names:
        frappe.delete_doc("DocField", docfield_name, force=1, ignore_permissions=True)

    return len(docfield_names)


def _drop_legacy_column_if_present() -> bool:
    if not frappe.db.table_exists(ENTRY_DOCTYPE):
        return False
    if not frappe.db.has_column(ENTRY_DOCTYPE, ENTRY_LINK_FIELD):
        return False

    frappe.db.sql_ddl(f"ALTER TABLE `{ENTRY_TABLE}` DROP COLUMN `{ENTRY_LINK_FIELD}`")
    return True


def execute():
    docfield_rows_removed = _delete_legacy_docfield_rows()
    column_removed = _drop_legacy_column_if_present()

    if docfield_rows_removed or column_removed:
        frappe.clear_cache()

    frappe.log_error(
        title="Communication Interaction entry legacy link cleanup",
        message=frappe.as_json(
            {
                "docfield_rows_removed": docfield_rows_removed,
                "column_removed": bool(column_removed),
            }
        ),
    )
