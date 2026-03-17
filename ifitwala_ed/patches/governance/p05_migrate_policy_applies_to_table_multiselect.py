# ifitwala_ed/patches/governance/p05_migrate_policy_applies_to_table_multiselect.py

from __future__ import annotations

import frappe

from ifitwala_ed.governance.policy_utils import (
    POLICY_APPLIES_TO_CHILD_DOCTYPE,
    POLICY_APPLIES_TO_LINK_FIELD,
    POLICY_APPLIES_TO_PARENTFIELD,
    ensure_policy_audience_records,
    get_policy_applies_to_tokens,
)


def execute():
    frappe.reload_doc("governance", "doctype", "policy_audience")
    frappe.reload_doc("governance", "doctype", "institutional_policy_audience")
    frappe.reload_doc("governance", "doctype", "institutional_policy")

    ensure_policy_audience_records()
    _backfill_policy_audience_rows_from_legacy_column()


def _backfill_policy_audience_rows_from_legacy_column() -> None:
    if not frappe.db.table_exists("Institutional Policy"):
        return
    if not frappe.db.table_exists(POLICY_APPLIES_TO_CHILD_DOCTYPE):
        return
    if not frappe.db.has_column("Institutional Policy", "applies_to"):
        return

    rows = frappe.db.sql(
        """
        SELECT name, applies_to
        FROM `tabInstitutional Policy`
        WHERE IFNULL(applies_to, '') != ''
        ORDER BY modified ASC
        """,
        as_dict=True,
    )
    for row in rows:
        policy_name = (row.get("name") or "").strip()
        if not policy_name:
            continue

        tokens = get_policy_applies_to_tokens(row.get("applies_to"))
        if not tokens:
            continue

        existing = {
            (value or "").strip()
            for value in frappe.get_all(
                POLICY_APPLIES_TO_CHILD_DOCTYPE,
                filters={
                    "parent": policy_name,
                    "parenttype": "Institutional Policy",
                    "parentfield": POLICY_APPLIES_TO_PARENTFIELD,
                },
                pluck=POLICY_APPLIES_TO_LINK_FIELD,
            )
            if (value or "").strip()
        }

        for token in tokens:
            if token in existing:
                continue
            frappe.get_doc(
                {
                    "doctype": POLICY_APPLIES_TO_CHILD_DOCTYPE,
                    "parent": policy_name,
                    "parenttype": "Institutional Policy",
                    "parentfield": POLICY_APPLIES_TO_PARENTFIELD,
                    POLICY_APPLIES_TO_LINK_FIELD: token,
                }
            ).insert(ignore_permissions=True)
