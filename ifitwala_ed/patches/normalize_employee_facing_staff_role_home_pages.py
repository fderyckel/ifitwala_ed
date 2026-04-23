# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Role"):
        return

    from ifitwala_ed.setup.setup import create_roles_with_homepage

    create_roles_with_homepage()
