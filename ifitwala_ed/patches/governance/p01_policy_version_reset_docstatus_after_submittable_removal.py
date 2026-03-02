# ifitwala_ed/patches/governance/p01_policy_version_reset_docstatus_after_submittable_removal.py

import frappe


def execute():
    if not frappe.db.table_exists("Policy Version"):
        return
    if not frappe.db.has_column("Policy Version", "docstatus"):
        return

    frappe.db.sql(
        """
        UPDATE `tabPolicy Version`
        SET docstatus = 0
        WHERE ifnull(docstatus, 0) != 0
        """
    )
