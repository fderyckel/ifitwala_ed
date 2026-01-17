# ifitwala_ed/stock/report/inventory_overdue_issues/inventory_overdue_issues.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	as_of_date = getdate(filters.get("as_of_date") or nowdate())

	rows = frappe.get_all(
		"Inventory Issue",
		filters={
			"docstatus": 1,
			"expected_return_date": ("<", as_of_date),
		},
		fields=[
			"name",
			"issue_from_location",
			"issued_to_type",
			"issued_to_employee",
			"issued_to_student",
			"issued_to_guardian",
			"issued_to_location",
			"expected_return_date",
		],
		order_by="expected_return_date asc",
	)

	for row in rows:
		row.issued_to = (
			row.issued_to_employee
			or row.issued_to_student
			or row.issued_to_guardian
			or row.issued_to_location
		)

	columns = [
		{"label": "Issue", "fieldname": "name", "fieldtype": "Link", "options": "Inventory Issue", "width": 180},
		{"label": "Issue From Location", "fieldname": "issue_from_location", "fieldtype": "Link", "options": "Location", "width": 180},
		{"label": "Issued To Type", "fieldname": "issued_to_type", "fieldtype": "Data", "width": 140},
		{"label": "Issued To", "fieldname": "issued_to", "fieldtype": "Data", "width": 180},
		{"label": "Expected Return Date", "fieldname": "expected_return_date", "fieldtype": "Date", "width": 140},
	]

	return columns, rows
