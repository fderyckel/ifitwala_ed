// ifitwala_ed/stock/report/inventory_issued_by_guardian/inventory_issued_by_guardian.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Inventory Issued By Guardian"] = {
	"filters": [
		{
			"fieldname": "guardian",
			"label": "Guardian",
			"fieldtype": "Link",
			"options": "Guardian"
		}
	]
};
