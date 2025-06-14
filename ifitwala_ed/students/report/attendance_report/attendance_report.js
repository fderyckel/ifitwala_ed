// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Attendance Report"] = {

	// ------------------------------------------------------------------ //
	// 1. Filters (single source of truth)                                //
	// ------------------------------------------------------------------ //
	filters: [
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School",
			reqd: 1
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1
		},
		{
			fieldname: "term",
			label: __("Term"),
			fieldtype: "Link",
			options: "Term"
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program"
		},
		{
			fieldname: "course",
			label: __("Course"),
			fieldtype: "Link",
			options: "Course"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
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
			fieldname: "instructor",
			label: __("Instructor"),
			fieldtype: "Link",
			options: "Instructor"
		},
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student"
		},
		{
			fieldname: "whole_day",
			label: __("Whole Day"),
			fieldtype: "Check"
		}
	],

	// ------------------------------------------------------------------ //
	// 2. Page setup                                                       //
	// ------------------------------------------------------------------ //
	onload(report) {
		report.page.set_title(__("Attendance Report"));

			// hide Course when Whole Day is ticked (safe after filters render)
		frappe.after_ajax(() => {
			const wholeDayFilter = report.get_filter("whole_day");
			const courseFilter   = report.get_filter("course");

			function toggle_course() {
				const isWhole = wholeDayFilter.get_value() === 1;
				report.toggle_filter_display("course", !isWhole);
				if (isWhole) courseFilter.set_value("");
			}
			if (wholeDayFilter) {
				wholeDayFilter.$input.on("change", toggle_course);
				toggle_course(); // initial state
			}
		});
	},

	// ------------------------------------------------------------------ //
	// 3. Column formatting                                                //
	// ------------------------------------------------------------------ //
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "percentage_present" && value !== undefined && value !== null) {
			const pct = parseFloat(value) || 0;
			let color = "orange";
			if (pct >= 95)  color = "green";
			else if (pct < 90) color = "red";
			return `<span class="indicator-pill ${color}">${pct}%</span>`;
		}

		if (column.fieldtype === "Int" && value !== undefined) {
			return `<div class="text-end">${value}</div>`;
		}
		return value;
	},

	// ------------------------------------------------------------------ //
	// 4. Datatable tweaks                                                 //
	// ------------------------------------------------------------------ //
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: false,
			noDataMessage: __("No attendance records match these filters.")
		});
	}
};
