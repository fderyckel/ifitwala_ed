// ifitwala_ed/stock/report/inventory_repair_queue/inventory_repair_queue.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Inventory Repair Queue"] = {
	"filters": [
		{
			"fieldname": "status",
			"label": "Status",
			"fieldtype": "Select",
			"options": "\nOpen\nIn Progress\nClosed",
			"default": ""
		}
	]
};
