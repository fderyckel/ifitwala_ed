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
        _backfill_employee_contact_link(employee_doc)


def _backfill_employee_contact_link(employee_doc) -> None:
    contact_name = employee_doc._get_or_create_primary_contact()
    if not contact_name:
        return

    employee_doc._ensure_contact_employee_link(contact_name)
    if employee_doc.empl_primary_contact != contact_name:
        employee_doc.empl_primary_contact = contact_name
        employee_doc.db_set("empl_primary_contact", contact_name, update_modified=False)
