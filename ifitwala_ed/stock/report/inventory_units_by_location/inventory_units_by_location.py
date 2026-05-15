# ifitwala_ed/stock/report/inventory_units_by_location/inventory_units_by_location.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import get_descendants_of


def execute(filters=None):
    filters = frappe._dict(filters or {})
    location = filters.get("location")

    location_list = None
    if location:
        location_list = [location] + (get_descendants_of("Location", location) or [])

    unit_filters = {}
    if location_list:
        unit_filters["current_location"] = ["in", location_list]
    else:
        unit_filters["current_location"] = ["is", "set"]

    rows = frappe.get_all(
        "Inventory Unit",
        filters=unit_filters,
        fields=[
            "name",
            "inventory_item",
            "serial_no",
            "asset_tag",
            "status",
            "condition",
            "current_location",
        ],
        order_by="current_location asc, inventory_item asc",
    )

    columns = [
        {
            "label": "Location",
            "fieldname": "current_location",
            "fieldtype": "Link",
            "options": "Location",
            "width": 180,
        },
        {
            "label": "Inventory Unit",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Inventory Unit",
            "width": 180,
        },
        {
            "label": "Inventory Item",
            "fieldname": "inventory_item",
            "fieldtype": "Link",
            "options": "Inventory Item",
            "width": 200,
        },
        {"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Data", "width": 160},
        {"label": "Asset Tag", "fieldname": "asset_tag", "fieldtype": "Data", "width": 140},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Condition", "fieldname": "condition", "fieldtype": "Data", "width": 120},
    ]

    return columns, rows
