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

		if (report?.page) {
			ensure_print_button(report.page);
		}
	},

	after_datatable_render(report) {
		if (report?.page) {
			ensure_print_button(report.page);
		}
	}
};

function ensure_print_button(page) {
	const KEY = "mi-print-btn";
	if (!page?.add_inner_button) return;
	if (page.inner_toolbar && page.inner_toolbar.find(`button[data-key="${KEY}"]`).length) {
		return;
	}

	const btn = page.add_inner_button(__("Print"), () => handle_report_print(), null);
	if (btn) {
		btn.attr("data-key", KEY);
		btn.removeClass("btn-default btn-primary").addClass("btn-info btn-sm");
	}
}

function handle_report_print() {
	const report = frappe.query_report;
	if (!report || typeof report.print_report !== "function") {
		frappe.msgprint(__("Print is not available on this report."));
		return;
	}

	frappe.ui.get_print_settings(
		false,
		(print_settings) => {
			print_settings = print_settings || {};
			report.print_report(print_settings);
		},
		report.report_doc && report.report_doc.letter_head,
		report.get_visible_columns ? report.get_visible_columns() : null
	);
}
