// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.query_reports["Attendance Report"] = {

	// ------------------------------------------------------------------ //
	// 2. Page setup                                                       //
	// ------------------------------------------------------------------ //
	onload(report) {
		report.page.set_title(__("Attendance Report"));
	},

	// ------------------------------------------------------------------ //
	// 3. Column formatting                                                //
	// ------------------------------------------------------------------ //
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "percentage_present" && value) {
			const pct = parseFloat(value);
			let color = "orange";
			if (pct >= 95)  color = "green";
			else if (pct < 90) color = "red";
			return `<span class="indicator-pill ${color}">${pct}%</span>`;
		}

		if (column.fieldtype === "Int") {
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
