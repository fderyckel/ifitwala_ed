# ifitwala_ed/stock/inventory/inventory_utils.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

try:
    from frappe.utils import unscrub
except ImportError:
    try:
        from frappe.utils.data import unscrub
    except ImportError:  # pragma: no cover - defensive fallback for older Frappe builds

        def unscrub(value):
            if not value:
                return value
            return " ".join(part.capitalize() for part in str(value).split("_"))


CUSTODY_FIELDS = (
    "current_location",
    "current_employee",
    "current_student",
    "current_guardian",
)


def coerce_datetime(value, *, fieldname="posting_datetime"):
    if value in (None, ""):
        return now_datetime()
    if isinstance(value, datetime):
        return value
    if isinstance(value, time):
        today = now_datetime().date().isoformat()
        return get_datetime(f"{today} {value.strftime('%H:%M:%S')}")
    if isinstance(value, timedelta):
        return now_datetime() + value
    if isinstance(value, str):
        try:
            return get_datetime(value)
        except Exception:
            _throw_time_coercion(value, fieldname)
    _throw_time_coercion(value, fieldname)


def resolve_issued_to(doc):
    issued_to_type = doc.get("issued_to_type")
    if not issued_to_type:
        frappe.throw(_("Issued To Type is required."))

    field_map = {
        "Employee": "issued_to_employee",
        "Student": "issued_to_student",
        "Guardian": "issued_to_guardian",
        "Location": "issued_to_location",
    }
    fieldname = field_map.get(issued_to_type)
    if not fieldname:
        frappe.throw(_("Invalid Issued To Type: {0}.").format(issued_to_type))

    filled = [fname for fname in field_map.values() if doc.get(fname)]
    if len(filled) != 1:
        frappe.throw(_("Exactly one Issued To field must be set."))

    value = doc.get(fieldname)
    if not value:
        frappe.throw(
            _("{0} is required for Issued To Type {1}.").format(frappe.bold(unscrub(fieldname)), issued_to_type)
        )

    return {"type": issued_to_type, "name": value}


def resolve_returned_from(doc):
    returned_from_type = doc.get("returned_from_type")
    if not returned_from_type:
        frappe.throw(_("Returned From Type is required."))

    field_map = {
        "Employee": "returned_from_employee",
        "Student": "returned_from_student",
        "Guardian": "returned_from_guardian",
        "Location": "returned_from_location",
    }
    fieldname = field_map.get(returned_from_type)
    if not fieldname:
        frappe.throw(_("Invalid Returned From Type: {0}.").format(returned_from_type))

    filled = [fname for fname in field_map.values() if doc.get(fname)]
    if len(filled) != 1:
        frappe.throw(_("Exactly one Returned From field must be set."))

    value = doc.get(fieldname)
    if not value:
        frappe.throw(
            _("{0} is required for Returned From Type {1}.").format(frappe.bold(unscrub(fieldname)), returned_from_type)
        )

    return {"type": returned_from_type, "name": value}


def set_unit_custody(unit_name, custody_fields):
    if not unit_name:
        frappe.throw(_("Inventory Unit is required for custody update."))

    count = sum(1 for field in CUSTODY_FIELDS if custody_fields.get(field))
    if count != 1:
        frappe.throw(_("Exactly one custody field must be set."))

    update = {field: custody_fields.get(field) for field in CUSTODY_FIELDS}
    frappe.db.set_value("Inventory Unit", unit_name, update, update_modified=True)


def assert_unit_in_location(unit_name, location):
    current = frappe.db.get_value("Inventory Unit", unit_name, "current_location")
    if current != location:
        frappe.throw(_("Inventory Unit {0} is not in Location {1}.").format(unit_name, location))


def assert_unit_held_by(unit_name, custodian_type, custodian_name):
    field_map = {
        "Employee": "current_employee",
        "Student": "current_student",
        "Guardian": "current_guardian",
        "Location": "current_location",
    }
    fieldname = field_map.get(custodian_type)
    if not fieldname:
        frappe.throw(_("Invalid custodian type: {0}.").format(custodian_type))

    current = frappe.db.get_value("Inventory Unit", unit_name, fieldname)
    if current != custodian_name:
        frappe.throw(_("Inventory Unit {0} is not held by {1} {2}.").format(unit_name, custodian_type, custodian_name))


def _throw_time_coercion(value, fieldname):
    debug = {
        "fieldname": fieldname,
        "value": str(value),
        "value_type": str(type(value)),
    }
    frappe.throw(
        _("Unable to coerce datetime for {0}. Debug: {1}.").format(fieldname, frappe.as_json(debug)),
        title=_("Time Coercion Error"),
    )
