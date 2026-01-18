# ifitwala_ed/stock/report/inventory_issued_by_employee/inventory_issued_by_employee.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	employee = filters.get("employee")

	unit_filters = {}
	if employee:
		unit_filters["current_employee"] = employee
	else:
		unit_filters["current_employee"] = ["is", "set"]

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
			"current_employee",
		],
		order_by="current_employee asc, inventory_item asc",
	)

	columns = [
		{"label": "Employee", "fieldname": "current_employee", "fieldtype": "Link", "options": "Employee", "width": 180},
		{"label": "Inventory Unit", "fieldname": "name", "fieldtype": "Link", "options": "Inventory Unit", "width": 180},
		{"label": "Inventory Item", "fieldname": "inventory_item", "fieldtype": "Link", "options": "Inventory Item", "width": 200},
		{"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Data", "width": 160},
		{"label": "Asset Tag", "fieldname": "asset_tag", "fieldtype": "Data", "width": 140},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Condition", "fieldname": "condition", "fieldtype": "Data", "width": 120},
	]

	return columns, rows
