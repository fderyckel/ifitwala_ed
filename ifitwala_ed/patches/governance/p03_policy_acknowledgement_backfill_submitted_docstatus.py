# ifitwala_ed/patches/governance/p03_policy_acknowledgement_backfill_submitted_docstatus.py

import frappe


def execute():
    if not frappe.db.table_exists("Policy Acknowledgement"):
        return
    if not frappe.db.has_column("Policy Acknowledgement", "docstatus"):
        return

    frappe.db.sql(
        """
        UPDATE `tabPolicy Acknowledgement`
        SET docstatus = 1
        WHERE ifnull(docstatus, 0) = 0
        """
    )
