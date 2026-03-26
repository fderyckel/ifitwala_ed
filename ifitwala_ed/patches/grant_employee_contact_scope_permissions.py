import frappe


def execute():
    if not frappe.db.table_exists("Custom DocPerm"):
        return

    from ifitwala_ed.setup.setup import grant_core_crm_permissions

    grant_core_crm_permissions()
