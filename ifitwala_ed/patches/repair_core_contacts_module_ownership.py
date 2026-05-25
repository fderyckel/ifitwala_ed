"""Restore Frappe core ownership of the Contacts module before orphan cleanup."""

from __future__ import annotations

CORE_CONTACTS_MODULE = "Contacts"
CORE_CONTACTS_APP = "frappe"


def execute():
    import frappe

    repair_core_contacts_module_ownership(frappe)


def repair_core_contacts_module_ownership(frappe_module) -> None:
    if frappe_module.db.exists("Module Def", CORE_CONTACTS_MODULE):
        current_app = frappe_module.db.get_value("Module Def", CORE_CONTACTS_MODULE, "app_name")
        if current_app != CORE_CONTACTS_APP:
            frappe_module.db.set_value(
                "Module Def",
                CORE_CONTACTS_MODULE,
                "app_name",
                CORE_CONTACTS_APP,
                update_modified=False,
            )
        return

    module_def = frappe_module.get_doc(
        {
            "doctype": "Module Def",
            "module_name": CORE_CONTACTS_MODULE,
            "app_name": CORE_CONTACTS_APP,
        }
    )
    module_def.insert(ignore_permissions=True)
