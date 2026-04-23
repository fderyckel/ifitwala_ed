# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Student") or not frappe.db.table_exists("Contact"):
        return

    student_names = frappe.get_all(
        "Student",
        filters={"student_email": ["is", "set"]},
        pluck="name",
        limit=100000,
    )

    for student_name in student_names:
        if not str(student_name or "").strip():
            continue

        frappe.get_doc("Student", student_name).ensure_contact_and_link()
