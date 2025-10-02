// Copyright (c) 2025, François de Ryckel
// For license information, please see license.txt

// ifitwala_ed/students/doctype/student/student_list.js

frappe.listview_settings["Student"] = {
	hide_name_column: true,

	// Ensure data is fetched for visible columns
	add_fields: ["enabled", "student_preferred_name", "student_gender", "cohort"],

	// Left-side status light
	get_indicator(doc) {
		return doc.enabled
			? [__("Active"), "green", "enabled,=,1"]
			: [__("Inactive"), "red", "enabled,=,0"];
	},

	// Column formatters
	formatters: {
		// Gender = colored pill
		student_gender(value) {
			const label = value || __("—");
			const color =
				value === "Female" ? "pink" :
				value === "Male" ? "light-blue" :
				"gray";
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(label)}</span>`;
		},

		// Status column uses the 'enabled' field (text only, row indicator already shows light)
		enabled(value) {
			return value ? __("Active") : __("Inactive");
		},
	},
};

