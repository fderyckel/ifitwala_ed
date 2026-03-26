import frappe


def execute():
    if not frappe.db.table_exists("Custom DocPerm"):
        return

    from ifitwala_ed.setup.setup import grant_role_read_select_to_hr

    grant_role_read_select_to_hr()
