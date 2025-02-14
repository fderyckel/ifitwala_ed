// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Program Enrollment Report"] = {
	"filters": [
		{
			"fieldname": "report_type",
			"label": "Report Type",
			"fieldtype": "Select", 
			"options": "\nProgram\nCourse",
			"default": "Program"
		},
		{
			"fieldname": "school",
			"label": "School",
			"fieldtype": "Link",
			"options": "School",
			"reqd": 1
		},
		{
			"fieldname": "program",
			"label": "Program",
			"fieldtype": "Link",
			"options": "Program",
			"reqd": 1
		},
		{
			"fieldname": "term",
			"label": "Term",
			"fieldtype": "Link",
			"options": "Term",
			"reqd": 0,
			"depends_on": "eval:doc.report_type=='Program'"
		},
		{
			"fieldname": "academic_year",
			"label": "Academic Year",
			"fieldtype": "Link",
			"options": "Academic Year",
			"reqd": 0,
			"depends_on": "eval:doc.report_type=='Course'"
		}
	],
	"chart_type": "bar",
	"default_columns": 2
};
