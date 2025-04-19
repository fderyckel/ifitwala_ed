// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Enrollment Report"] = {
	"filters": [
		{
			"fieldname": "report_type",
			"label": "Report Type",
			"fieldtype": "Select",
			"options": "\nProgram\nCourse\nCohort",
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
			"options": "Program", 
			"depends_on": "eval:doc.school",
			"get_query": function () {
				let school = frappe.query_report.get_filter_value("school");
				if (school) {
					return {
						filters: {
							school: school
						}
					};
				}
			}
		},
		{
			"fieldname": "student_cohort",
			"label": "Cohort",
			"fieldtype": "Link",
			"options": "Student Cohort",
			"depends_on": "eval:doc.report_type=='Cohort'"
		},			
		{
			"fieldname": "academic_year",
			"label": "Academic Year",
			"fieldtype": "Link",
			"options": "Academic Year",
			"get_query": function (doc) {
				let school = frappe.query_report.get_filter_value("school");
				if (school) {
					return {
						query: "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.get_academic_years_for_school",
						filters: { school: school }
					};
				}
			}
		}
	],
	"chart_type": "bar",
	"default_columns": 2,
	
};
