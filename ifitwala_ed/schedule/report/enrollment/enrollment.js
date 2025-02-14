// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Enrollment"] = {
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
					"options": "School"
			},
			{
					"fieldname": "program",
					"label": "Program",
					"fieldtype": "Link",
					"options": "Program"
			},
			{
					"fieldname": "academic_year",
					"label": "Academic Year",
					"fieldtype": "Link",
					"options": "Academic Year",
					"depends_on": "eval:doc.report_type=='Course' || doc.report_type=='Program'"
			}
	],
	"chart_type": "bar",
	"default_columns": 2
};
