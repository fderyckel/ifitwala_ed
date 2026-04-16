import frappe


def execute():
    if not frappe.db.table_exists("Leave Type"):
        return

    from ifitwala_ed.setup.setup import create_default_leave_types

    create_default_leave_types()
