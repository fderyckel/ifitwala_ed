import frappe


def execute():
    if not frappe.db.table_exists("Address Template"):
        return

    from ifitwala_ed.setup.setup import ensure_default_address_template

    ensure_default_address_template()
