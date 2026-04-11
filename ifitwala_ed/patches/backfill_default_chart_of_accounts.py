# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Organization") or not frappe.db.table_exists("Account"):
        return

    from ifitwala_ed.accounting.coa_utils import create_coa_for_organization
    from ifitwala_ed.setup.doctype.organization.organization import VIRTUAL_ROOT

    organizations = frappe.get_all(
        "Organization",
        filters={"name": ["!=", VIRTUAL_ROOT]},
        pluck="name",
    )

    for organization in organizations:
        if frappe.db.count("Account", filters={"organization": organization}) and frappe.db.exists(
            "Accounts Settings", organization
        ):
            continue

        create_coa_for_organization(organization)
