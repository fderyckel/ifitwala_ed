# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import cstr


def execute():
    if not frappe.db.table_exists("Employee") or not frappe.db.table_exists("Contact"):
        return

    employee_names = frappe.get_all(
        "Employee",
        filters={"user_id": ["is", "set"]},
        pluck="name",
        limit=100000,
    )

    for employee_name in employee_names:
        if not cstr(employee_name).strip():
            continue

        employee_doc = frappe.get_doc("Employee", employee_name)
        employee_doc._ensure_primary_contact()
