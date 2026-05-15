// ifitwala_ed/stock/report/inventory_overdue_issues/inventory_overdue_issues.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Inventory Overdue Issues"] = {
	"filters": [
		{
			"fieldname": "as_of_date",
			"label": "As Of Date",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		}
	]
};
