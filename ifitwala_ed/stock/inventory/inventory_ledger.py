# ifitwala_ed/stock/inventory/inventory_ledger.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from ifitwala_ed.stock.inventory.inventory_utils import coerce_datetime


def make_ledger_entries(voucher_type, voucher_name, posting_datetime, rows):
    if not rows:
        frappe.throw(_("No ledger rows provided."))
    if not voucher_type or not voucher_name:
        frappe.throw(_("Voucher Type and Voucher Name are required."))

    posting_dt = coerce_datetime(posting_datetime, fieldname="posting_datetime")
    owner = frappe.session.user
    timestamp = now_datetime()

    fields = [
        "name",
        "inventory_item",
        "inventory_unit",
        "from_location",
        "to_location",
        "qty_change",
        "voucher_type",
        "voucher_name",
        "posting_datetime",
        "remarks",
        "owner",
        "creation",
        "modified",
        "modified_by",
        "docstatus",
    ]

    values = []
    for row in rows:
        if not row.get("inventory_item"):
            frappe.throw(_("Inventory Item is required for ledger rows."))

        entry = {
            "name": frappe.generate_hash(length=12),
            "inventory_item": row.get("inventory_item"),
            "inventory_unit": row.get("inventory_unit"),
            "from_location": row.get("from_location"),
            "to_location": row.get("to_location"),
            "qty_change": flt(row.get("qty_change") or 0),
            "voucher_type": voucher_type,
            "voucher_name": voucher_name,
            "posting_datetime": posting_dt,
            "remarks": row.get("remarks"),
            "owner": owner,
            "creation": timestamp,
            "modified": timestamp,
            "modified_by": owner,
            "docstatus": 0,
        }
        values.append([entry.get(field) for field in fields])

    frappe.db.bulk_insert("Inventory Ledger Entry", fields, values)
