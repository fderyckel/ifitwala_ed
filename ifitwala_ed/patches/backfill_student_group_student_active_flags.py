# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Student Group Student"):
        return

    frappe.db.sql(
        """
        UPDATE `tabStudent Group Student`
        SET active = 1
        WHERE active IS NULL
        """
    )
