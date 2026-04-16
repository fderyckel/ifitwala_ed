from __future__ import annotations

import frappe


def execute():
    from ifitwala_ed.accounting.coa_utils import DEFAULT_CHART_TEMPLATE
    from ifitwala_ed.accounting.doctype.account.chart_of_accounts.chart_of_accounts import (
        get_chart,
        sync_account_types_from_chart,
    )

    chart = get_chart(DEFAULT_CHART_TEMPLATE)
    if not chart:
        return

    organizations = frappe.get_all("Organization", pluck="name", limit=5000)
    for organization in organizations:
        if not frappe.db.count("Account", {"organization": organization}):
            continue
        sync_account_types_from_chart(organization, chart=chart)
