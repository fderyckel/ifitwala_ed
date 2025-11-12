// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Medical Info And Emergency Contact"] = {
	filters: [
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School"
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program"
		},
		{
			fieldname: "student_group",
			label: __("Student Group"),
			fieldtype: "Link",
			options: "Student Group",
			reqd: 1
		}
	],

	onload(report) {
		const school_filter = report.get_filter("school");
		const student_group_filter = report.get_filter("student_group");

		if (student_group_filter) {
			student_group_filter.get_query = () => ({
				query: "ifitwala_ed.utilities.link_queries.student_group_link_query",
				filters: {
					school: frappe.query_report.get_filter_value("school"),
					program: frappe.query_report.get_filter_value("program")
				}
			});
		}

		if (!school_filter) return;

		frappe.call({
			method: "ifitwala_ed.utilities.school_tree.get_user_default_school",
			callback: (r) => {
				const user_school = (r && r.message) || "";

				school_filter.get_query = () => ({
					query: "ifitwala_ed.utilities.school_tree.get_school_descendants",
					filters: { root: user_school || frappe.query_report.get_filter_value("school") }
				});

				if (!frappe.query_report.get_filter_value("school") && user_school) {
					frappe.query_report.set_filter_value("school", user_school);
				}
			}
		});
	}
};
