# ifitwala_ed/stock/inventory/inventory_validations.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

from ifitwala_ed.stock.inventory.inventory_utils import CUSTODY_FIELDS, resolve_issued_to, resolve_returned_from


def validate_issue(doc):
	resolve_issued_to(doc)
	if not doc.get("issue_from_location"):
		frappe.throw(_("Issue From Location is required."))

	items = _get_doc_items(doc)
	item_map = _get_item_map(items)
	unit_map = _get_unit_map(items)

	for idx, row in enumerate(items, start=1):
		_validate_issue_row(doc, row, idx, item_map, unit_map)


def validate_return(doc):
	returned_from = resolve_returned_from(doc)
	if not doc.get("return_to_location"):
		frappe.throw(_("Return To Location is required."))

	items = _get_doc_items(doc)
	item_map = _get_item_map(items)
	unit_map = _get_unit_map(items)

	for idx, row in enumerate(items, start=1):
		_validate_return_row(doc, row, idx, returned_from, item_map, unit_map)


def validate_transfer(doc):
	if not doc.get("from_location") or not doc.get("to_location"):
		frappe.throw(_("From Location and To Location are required."))
	if doc.from_location == doc.to_location:
		frappe.throw(_("From Location and To Location cannot be the same."))

	items = _get_doc_items(doc)
	item_map = _get_item_map(items)
	unit_map = _get_unit_map(items)

	for idx, row in enumerate(items, start=1):
		_validate_transfer_row(doc, row, idx, item_map, unit_map)


def validate_unit_custody(unit_doc_or_fields):
	fields = {}
	for fieldname in CUSTODY_FIELDS:
		if isinstance(unit_doc_or_fields, dict):
			fields[fieldname] = unit_doc_or_fields.get(fieldname)
		else:
			fields[fieldname] = getattr(unit_doc_or_fields, fieldname, None)

	count = sum(1 for field in CUSTODY_FIELDS if fields.get(field))
	if count != 1:
		frappe.throw(_("Exactly one custody field must be set."))


def _get_doc_items(doc):
	items = doc.get("items") or []
	if not items:
		frappe.throw(_("At least one item row is required."))
	return items


def _get_item_map(items):
	item_names = {row.inventory_item for row in items if row.inventory_item}
	if not item_names:
		return {}
	rows = frappe.get_all(
		"Inventory Item",
		filters={"name": ["in", list(item_names)]},
		fields=["name", "has_serial_no", "is_consumable"],
	)
	return {row.name: row for row in rows}


def _get_unit_map(items):
	unit_names = {row.inventory_unit for row in items if row.inventory_unit}
	if not unit_names:
		return {}
	rows = frappe.get_all(
		"Inventory Unit",
		filters={"name": ["in", list(unit_names)]},
		fields=[
			"name",
			"inventory_item",
			"status",
			"current_location",
			"current_employee",
			"current_student",
			"current_guardian",
		],
	)
	return {row.name: row for row in rows}


def _validate_issue_row(doc, row, idx, item_map, unit_map):
	if not row.inventory_item:
		frappe.throw(_("Row {0}: Inventory Item is required.").format(idx))

	item = item_map.get(row.inventory_item)
	if not item:
		frappe.throw(_("Row {0}: Inventory Item {1} not found.").format(idx, row.inventory_item))

	has_serial_no = cint(item.has_serial_no)
	is_consumable = cint(item.is_consumable)
	qty = flt(row.qty or 0)

	if is_consumable:
		if row.inventory_unit:
			frappe.throw(_("Row {0}: Consumables cannot use Inventory Unit.").format(idx))
		if qty <= 0:
			frappe.throw(_("Row {0}: Consumable qty must be greater than 0.").format(idx))

	if has_serial_no:
		if not row.inventory_unit:
			frappe.throw(_("Row {0}: Inventory Unit is required for serial items.").format(idx))
		if qty != 1:
			frappe.throw(_("Row {0}: Serial item qty must be 1.").format(idx))

	if row.inventory_unit:
		unit = unit_map.get(row.inventory_unit)
		if not unit:
			frappe.throw(_("Row {0}: Inventory Unit {1} not found.").format(idx, row.inventory_unit))
		if unit.inventory_item != row.inventory_item:
			frappe.throw(_("Row {0}: Inventory Unit does not match Inventory Item.").format(idx))
		if unit.status != "Available":
			frappe.throw(_("Row {0}: Inventory Unit must be Available.").format(idx))
		if unit.current_location != doc.issue_from_location:
			frappe.throw(_("Row {0}: Inventory Unit is not in the Issue From Location.").format(idx))


def _validate_return_row(doc, row, idx, returned_from, item_map, unit_map):
	if not row.inventory_item:
		frappe.throw(_("Row {0}: Inventory Item is required.").format(idx))

	item = item_map.get(row.inventory_item)
	if not item:
		frappe.throw(_("Row {0}: Inventory Item {1} not found.").format(idx, row.inventory_item))

	has_serial_no = cint(item.has_serial_no)
	is_consumable = cint(item.is_consumable)
	qty = flt(row.qty or 0)

	if is_consumable:
		if row.inventory_unit:
			frappe.throw(_("Row {0}: Consumables cannot use Inventory Unit.").format(idx))
		if qty <= 0:
			frappe.throw(_("Row {0}: Consumable qty must be greater than 0.").format(idx))

	if has_serial_no and not row.inventory_unit:
		frappe.throw(_("Row {0}: Inventory Unit is required for serial items.").format(idx))

	if row.inventory_unit:
		unit = unit_map.get(row.inventory_unit)
		if not unit:
			frappe.throw(_("Row {0}: Inventory Unit {1} not found.").format(idx, row.inventory_unit))
		if unit.inventory_item != row.inventory_item:
			frappe.throw(_("Row {0}: Inventory Unit does not match Inventory Item.").format(idx))
		if unit.status not in {"Issued", "Under Repair"}:
			frappe.throw(_("Row {0}: Inventory Unit must be Issued or Under Repair.").format(idx))

		field_map = {
			"Employee": "current_employee",
			"Student": "current_student",
			"Guardian": "current_guardian",
			"Location": "current_location",
		}
		fieldname = field_map.get(returned_from["type"])
		if not fieldname:
			frappe.throw(_("Row {0}: Invalid Returned From Type.").format(idx))

		current_holder = unit.get(fieldname)
		if current_holder != returned_from["name"]:
			frappe.throw(_("Row {0}: Inventory Unit is not held by the selected custodian.").format(idx))


def _validate_transfer_row(doc, row, idx, item_map, unit_map):
	if not row.inventory_item:
		frappe.throw(_("Row {0}: Inventory Item is required.").format(idx))

	item = item_map.get(row.inventory_item)
	if not item:
		frappe.throw(_("Row {0}: Inventory Item {1} not found.").format(idx, row.inventory_item))

	has_serial_no = cint(item.has_serial_no)
	is_consumable = cint(item.is_consumable)
	qty = flt(row.qty or 0)

	if is_consumable and row.inventory_unit:
		frappe.throw(_("Row {0}: Consumables cannot use Inventory Unit.").format(idx))

	if has_serial_no:
		if not row.inventory_unit:
			frappe.throw(_("Row {0}: Inventory Unit is required for serial items.").format(idx))
		if qty != 1:
			frappe.throw(_("Row {0}: Serial item qty must be 1.").format(idx))

	if row.inventory_unit and qty != 1:
		frappe.throw(_("Row {0}: Inventory Unit rows must have qty 1.").format(idx))

	if row.inventory_unit:
		unit = unit_map.get(row.inventory_unit)
		if not unit:
			frappe.throw(_("Row {0}: Inventory Unit {1} not found.").format(idx, row.inventory_unit))
		if unit.inventory_item != row.inventory_item:
			frappe.throw(_("Row {0}: Inventory Unit does not match Inventory Item.").format(idx))
