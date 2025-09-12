// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Copyright (c) 2025
// Ifitwala Ed - Student Log + Follow-ups (Report JS)

frappe.query_reports["Student Log + Follow-ups"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student"
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program"
		},
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School"
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year"
		},
		{
			fieldname: "log_type",
			label: __("Log Type"),
			fieldtype: "Link",
			options: "Student Log Type"
		},
		{
			fieldname: "follow_up_status",
			label: __("Follow-up Status"),
			fieldtype: "Select",
			options: ["", "Open", "In Progress", "Closed"]
		},
		{
			fieldname: "requires_follow_up",
			label: __("Requires Follow-up"),
			fieldtype: "Check"
		},
		{
			fieldname: "author",
			label: __("Author (Log)"),
			fieldtype: "Link",
			options: "User"
		},
		{
			fieldname: "fu_author",
			label: __("Author (Follow-up)"),
			fieldtype: "Link",
			options: "User"
		}
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Status badge formatting
		if (column.fieldname === "follow_up_status" && value) {
			let color = "secondary";
			if (value === "In Progress") color = "primary";
			if (value === "Closed") color = "dark";

			return `<span class="badge bg-${color}">${value}</span>`;
		}

		// Visibility icons (👤 / 👪) — already rendered server-side, just ensure style
		if (column.fieldname === "visibility" && value) {
			return `<span style="font-size:1.1em">${value}</span>`;
		}

		// Snippet: show tooltip with full text
		if ((column.fieldname === "log_snippet" || column.fieldname === "follow_up_snippet") && value) {
			return `<span title="${frappe.utils.escape_html(value)}">${value}</span>`;
		}

		return value;
	}
};
