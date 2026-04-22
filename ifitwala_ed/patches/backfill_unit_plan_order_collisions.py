# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.curriculum import planning


def execute():
    if not frappe.db.table_exists("Unit Plan"):
        return

    rows = frappe.get_all(
        "Unit Plan",
        fields=["name", "course_plan", "unit_order"],
        order_by="course_plan asc, unit_order asc, creation asc, name asc",
        limit=0,
    )
    if not rows:
        return

    seen_orders_by_course_plan: dict[str, set[int]] = {}
    for row in rows:
        unit_name = str(row.get("name") or "").strip()
        course_plan = str(row.get("course_plan") or "").strip()
        unit_order = int(row.get("unit_order") or 0)
        if not unit_name or not course_plan or unit_order <= 0:
            continue

        seen_orders = seen_orders_by_course_plan.setdefault(course_plan, set())
        if unit_order not in seen_orders:
            seen_orders.add(unit_order)
            continue

        next_order = planning.next_unit_order(course_plan)
        frappe.db.set_value("Unit Plan", unit_name, {"unit_order": next_order}, update_modified=False)
        seen_orders.add(next_order)
