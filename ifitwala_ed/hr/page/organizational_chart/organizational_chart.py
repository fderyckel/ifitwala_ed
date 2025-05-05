# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import os
import frappe
from frappe.query_builder.functions import Count

@frappe.whitelist()
def get_children(parent=None, organization=None, exclude_node=None):
    # … your existing filter setup …

    employees = frappe.get_all(
        "Employee",
        fields=[
            "employee_full_name as name",
            "name as id",
            "lft",
            "rgt",
            "reports_to",
            "employee_image as image",  # e.g. "/files/employee/person1.png"
            "designation as title",
        ],
        filters=filters,
        order_by="name",
    )

    card_dir = frappe.get_site_path("public", "files", "resized_gallery", "employee")

    for emp in employees:
        orig_url = emp.image or ""
        card_url = None

        # only if the original comes from /files/employee/
        if orig_url.startswith("/files/employee/") and os.path.isdir(card_dir):
            # strip path, get "person1.png" or "person1.jpg"
            filename = orig_url.rsplit("/", 1)[-1]
            name, _ext = os.path.splitext(filename)

            # build the .webp card filename
            card_filename = f"card_{name}.webp"
            disk_path = os.path.join(card_dir, card_filename)

            if os.path.exists(disk_path):
                card_url = f"/files/resized_gallery/employee/{card_filename}"

        # pick the card if it exists, else the original
        emp.image = card_url or orig_url

        # compute connections as before
        emp.connections = get_connections(emp.id, emp.lft, emp.rgt)
        emp.expandable = bool(emp.connections)

    return employees


def get_connections(employee: str, lft: int, rgt: int) -> int:
    Employee = frappe.qb.DocType("Employee")
    query = (
        frappe.qb.from_(Employee)
        .select(Count(Employee.name))
        .where(
            (Employee.lft > lft)
            & (Employee.rgt < rgt)
            & (Employee.status == "Active")
        )
    ).run()
    return query[0][0]

