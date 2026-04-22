from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Employee") or not frappe.db.table_exists("User"):
        return

    employee_rows = frappe.get_all(
        "Employee",
        filters={"user_id": ["is", "set"]},
        fields=["name", "user_id"],
        limit=100000,
    )

    for employee_row in employee_rows:
        _backfill_employee_managed_access(employee_row)


def _backfill_employee_managed_access(employee_row: dict) -> None:
    employee_name = str(employee_row.get("name") or "").strip()
    user_id = str(employee_row.get("user_id") or "").strip()
    if not employee_name or not user_id:
        return
    if not frappe.db.exists("User", user_id):
        return

    employee_doc = frappe.get_doc("Employee", employee_name)

    from ifitwala_ed.hr.employee_access import sync_user_access_from_employee

    sync_user_access_from_employee(employee_doc)
