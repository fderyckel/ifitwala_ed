# ifitwala_ed/api/inventory.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

ISSUE_FIELDS = (
    "issue_from_location",
    "issued_to_type",
    "issued_to_employee",
    "issued_to_student",
    "issued_to_guardian",
    "issued_to_location",
    "expected_return_date",
    "terms_accepted",
    "accepted_by_name",
    "accepted_on",
    "acknowledgment_attachment",
    "notes",
)

RETURN_FIELDS = (
    "return_to_location",
    "returned_from_type",
    "returned_from_employee",
    "returned_from_student",
    "returned_from_guardian",
    "returned_from_location",
    "posting_datetime",
    "notes",
)

ISSUE_ITEM_FIELDS = (
    "inventory_item",
    "inventory_unit",
    "qty",
    "condition_out",
    "remarks",
)

RETURN_ITEM_FIELDS = (
    "inventory_item",
    "inventory_unit",
    "qty",
    "condition_in",
    "remarks",
)


@frappe.whitelist()
def bulk_issue(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    items = data.get("items") or []
    if not isinstance(items, list):
        frappe.throw(_("Items must be a list."))
    if len(items) > 500:
        frappe.throw(_("Bulk issue supports up to 500 rows."))

    doc = frappe.new_doc("Inventory Issue")
    _apply_fields(doc, data, ISSUE_FIELDS)
    _apply_child_rows(doc, items, ISSUE_ITEM_FIELDS)
    doc.insert()
    doc.submit()
    return {"name": doc.name}


@frappe.whitelist()
def bulk_return(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    items = data.get("items") or []
    if not isinstance(items, list):
        frappe.throw(_("Items must be a list."))
    if len(items) > 500:
        frappe.throw(_("Bulk return supports up to 500 rows."))

    doc = frappe.new_doc("Inventory Return")
    _apply_fields(doc, data, RETURN_FIELDS)
    _apply_child_rows(doc, items, RETURN_ITEM_FIELDS)
    doc.insert()
    doc.submit()
    return {"name": doc.name}


def _normalize_payload(payload, kwargs):
    data = payload if payload is not None else kwargs
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw(_("Payload must be a dict."))
    return data


def _apply_fields(doc, data, fieldnames):
    for fieldname in fieldnames:
        if fieldname in data:
            doc.set(fieldname, data.get(fieldname))


def _apply_child_rows(doc, items, fieldnames):
    for row in items:
        if not isinstance(row, dict):
            frappe.throw(_("Each item row must be a dict."))
        payload = {field: row.get(field) for field in fieldnames}
        doc.append("items", payload)
