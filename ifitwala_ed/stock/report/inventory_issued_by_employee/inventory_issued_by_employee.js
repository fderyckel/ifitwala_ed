// ifitwala_ed/stock/report/inventory_issued_by_employee/inventory_issued_by_employee.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Inventory Issued By Employee"] = {
	"filters": [
		{
			"fieldname": "employee",
			"label": "Employee",
			"fieldtype": "Link",
			"options": "Employee"
		}
	]
};
