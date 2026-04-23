# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

ACADEMIC_STAFF_ROLE = "Academic Staff"


def execute():
    if not frappe.db.table_exists("Student Log") or not frappe.db.table_exists("Student Log Next Step"):
        return

    log_rows = frappe.get_all(
        "Student Log",
        fields=["name", "next_step", "follow_up_role"],
        filters={"requires_follow_up": 1},
        order_by="creation asc, name asc",
        limit=0,
    )
    rows_missing_role = [row for row in (log_rows or []) if not str(row.get("follow_up_role") or "").strip()]
    if not rows_missing_role:
        return

    next_step_names = sorted(
        {
            str(row.get("next_step") or "").strip()
            for row in rows_missing_role
            if str(row.get("next_step") or "").strip()
        }
    )
    if not next_step_names:
        return

    next_step_rows = frappe.get_all(
        "Student Log Next Step",
        fields=["name", "associated_role"],
        filters={"name": ["in", next_step_names]},
        order_by="modified asc, name asc",
        limit=0,
    )
    role_by_next_step = {
        str(row.get("name") or "").strip(): (str(row.get("associated_role") or "").strip() or ACADEMIC_STAFF_ROLE)
        for row in (next_step_rows or [])
        if str(row.get("name") or "").strip()
    }

    for row in rows_missing_role:
        log_name = str(row.get("name") or "").strip()
        next_step = str(row.get("next_step") or "").strip()
        if not log_name or not next_step:
            continue

        resolved_role = role_by_next_step.get(next_step)
        if not resolved_role:
            continue

        frappe.db.set_value("Student Log", log_name, {"follow_up_role": resolved_role}, update_modified=False)
