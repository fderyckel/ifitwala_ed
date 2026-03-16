# ifitwala_ed/patches/admission/p02_backfill_student_guardian_can_consent.py

import frappe


def execute():
    if not frappe.db.table_exists("Student Guardian"):
        return
    if not frappe.db.has_column("Student Guardian", "can_consent"):
        return

    frappe.db.sql(
        """
        UPDATE `tabStudent Guardian`
        SET can_consent = 1
        WHERE can_consent IS NULL
        """
    )
