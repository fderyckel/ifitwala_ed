# ifitwala_ed/patches/governance/p04_policy_version_backfill_based_on_version.py

import frappe


def execute():
    if not frappe.db.table_exists("Policy Version"):
        return

    if not frappe.db.has_column("Policy Version", "based_on_version"):
        frappe.db.sql(
            """
            ALTER TABLE `tabPolicy Version`
            ADD COLUMN `based_on_version` VARCHAR(140)
            """
        )

    if not frappe.db.has_column("Policy Version", "amended_from"):
        return

    frappe.db.sql(
        """
        UPDATE `tabPolicy Version`
        SET based_on_version = amended_from
        WHERE ifnull(based_on_version, '') = ''
          AND ifnull(amended_from, '') != ''
        """
    )
