// Copyright (c) 2025, François de Ryckel 
// For license information, please see license.txt

// ifitwala_ed/students/doctype/student/student_list.js

frappe.listview_settings["Student"] = {
	hide_name_column: true,

	// make sure these come in the initial fetch
	add_fields: ["enabled", "student_gender", "cohort", "student_first_language"],

	// Row-level status light (left side)
	get_indicator(doc) {
		return doc.enabled
			? [__("Active"), "green", "enabled,=,1"]
			: [__("Inactive"), "red", "enabled,=,0"];
	},

	// Per-column formatters
	formatters: {
		// Colored pill in the Student Gender column
		student_gender(value) {
			const label = value || __("—");
			const color =
				value === "Female" ? "pink" :
				value === "Male" ? "light-blue" :
				"gray";
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(label)}</span>`;
		},
	},
};
