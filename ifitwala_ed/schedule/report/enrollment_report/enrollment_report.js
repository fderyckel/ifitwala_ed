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
			"options": "School",
			get_query: function() {
				return {
					filters: {
						name: ["in", window.allowed_schools || []]
					}
				};
			}
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

	onload: function(report) {
		frappe.breadcrumbs.add("School Settings", "Settings", "/desk/admin");
		frappe.call({
			method: "ifitwala_ed.school_settings.school_settings_utils.get_user_allowed_schools",
			callback: function(r) {
				const allowed_schools = r.message || [];
				window.allowed_schools = allowed_schools;
				if (!allowed_schools.length) {
					frappe.msgprint(__("You do not have a default school assigned. Please contact your administrator."));
					return;
				}
				const school_filter = report.get_filter("school");
				const default_school = allowed_schools[0];
				school_filter.set_value(default_school);
				if (allowed_schools.length === 1) {
					school_filter.df.read_only = 1;
					school_filter.refresh();
				} else {
					school_filter.df.read_only = 0;
					school_filter.refresh();
				}
			}
		});
	},

	"chart_type": "bar",
	"default_columns": 2,

};
