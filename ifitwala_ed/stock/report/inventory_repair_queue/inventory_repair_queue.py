# ifitwala_ed/stock/report/inventory_repair_queue/inventory_repair_queue.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	status = filters.get("status")

	query_filters = {}
	if status:
		query_filters["status"] = status
	else:
		query_filters["status"] = ["in", ["Open", "In Progress"]]

	rows = frappe.get_all(
		"Inventory Repair Ticket",
		filters=query_filters,
		fields=[
			"name",
			"inventory_unit",
			"issue_summary",
			"status",
			"opened_on",
			"closed_on",
		],
		order_by="opened_on desc",
	)

	columns = [
		{"label": "Repair Ticket", "fieldname": "name", "fieldtype": "Link", "options": "Inventory Repair Ticket", "width": 180},
		{"label": "Inventory Unit", "fieldname": "inventory_unit", "fieldtype": "Link", "options": "Inventory Unit", "width": 180},
		{"label": "Issue Summary", "fieldname": "issue_summary", "fieldtype": "Data", "width": 200},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Opened On", "fieldname": "opened_on", "fieldtype": "Datetime", "width": 160},
		{"label": "Closed On", "fieldname": "closed_on", "fieldtype": "Datetime", "width": 160},
	]

	return columns, rows
