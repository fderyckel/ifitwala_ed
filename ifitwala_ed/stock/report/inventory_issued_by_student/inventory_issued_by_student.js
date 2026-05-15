// ifitwala_ed/stock/report/inventory_issued_by_student/inventory_issued_by_student.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Inventory Issued By Student"] = {
	"filters": [
		{
			"fieldname": "student",
			"label": "Student",
			"fieldtype": "Link",
			"options": "Student"
		}
	]
};
