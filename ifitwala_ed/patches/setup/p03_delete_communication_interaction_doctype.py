# ifitwala_ed/patches/setup/p03_delete_communication_interaction_doctype.py

from __future__ import annotations

import frappe

LEGACY_DOCTYPE = "Communication Interaction"
LEGACY_TABLE = "tabCommunication Interaction"


def _delete_legacy_doctype_metadata() -> bool:
    if not frappe.db.exists("DocType", LEGACY_DOCTYPE):
        return False

    frappe.delete_doc("DocType", LEGACY_DOCTYPE, force=1, ignore_permissions=True)
    return True


def _drop_legacy_table_if_present() -> bool:
    if not frappe.db.table_exists(LEGACY_DOCTYPE):
        return False

    frappe.db.sql_ddl(f"DROP TABLE `{LEGACY_TABLE}`")
    return True


def execute():
    doctype_removed = _delete_legacy_doctype_metadata()
    table_removed = _drop_legacy_table_if_present()

    if doctype_removed or table_removed:
        frappe.clear_cache()

    frappe.log_error(
        title="Communication Interaction doctype cleanup",
        message=frappe.as_json(
            {
                "doctype_removed": bool(doctype_removed),
                "table_removed": bool(table_removed),
            }
        ),
    )
