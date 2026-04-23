# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict

import frappe


def execute():
    if not frappe.db.table_exists("Student Referral") or not frappe.db.table_exists("Referral Case"):
        return

    cases_by_referral: dict[str, list[str]] = defaultdict(list)
    case_rows = frappe.get_all(
        "Referral Case",
        fields=["name", "referral"],
        filters={"referral": ["is", "set"]},
        order_by="creation asc, name asc",
        limit=0,
    )
    for row in case_rows or []:
        referral_name = str(row.get("referral") or "").strip()
        case_name = str(row.get("name") or "").strip()
        if referral_name and case_name:
            cases_by_referral[referral_name].append(case_name)

    if not cases_by_referral:
        return

    referral_rows = frappe.get_all(
        "Student Referral",
        fields=["name", "referral_case"],
        filters={"name": ["in", sorted(cases_by_referral)]},
        order_by="creation asc, name asc",
        limit=0,
    )
    for row in referral_rows or []:
        referral_name = str(row.get("name") or "").strip()
        if not referral_name:
            continue

        linked_cases = cases_by_referral.get(referral_name, [])
        if len(linked_cases) != 1:
            continue

        target_case = linked_cases[0]
        current_case = str(row.get("referral_case") or "").strip()
        if current_case == target_case:
            continue

        frappe.db.set_value(
            "Student Referral",
            referral_name,
            {"referral_case": target_case},
            update_modified=False,
        )
