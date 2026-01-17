# ifitwala_ed/stock/report/inventory_issued_by_student/inventory_issued_by_student.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	student = filters.get("student")

	unit_filters = {}
	if student:
		unit_filters["current_student"] = student
	else:
		unit_filters["current_student"] = ["is", "set"]

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
			"current_student",
		],
		order_by="current_student asc, inventory_item asc",
	)

	columns = [
		{"label": "Student", "fieldname": "current_student", "fieldtype": "Link", "options": "Student", "width": 180},
		{"label": "Inventory Unit", "fieldname": "name", "fieldtype": "Link", "options": "Inventory Unit", "width": 180},
		{"label": "Inventory Item", "fieldname": "inventory_item", "fieldtype": "Link", "options": "Inventory Item", "width": 200},
		{"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Data", "width": 160},
		{"label": "Asset Tag", "fieldname": "asset_tag", "fieldtype": "Data", "width": 140},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Condition", "fieldname": "condition", "fieldtype": "Data", "width": 120},
	]

	return columns, rows
