// ifitwala_ed/stock/report/inventory_units_by_location/inventory_units_by_location.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Inventory Units By Location"] = {
	"filters": [
		{
			"fieldname": "location",
			"label": "Location",
			"fieldtype": "Link",
			"options": "Location"
		}
	]
};
