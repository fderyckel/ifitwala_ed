// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Student Group"] = {
	onload: function(listview) {
		listview.page.fields_dict['academic_year'].get_query = function() {
			return { query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.academic_year_link_query" };
		};
	},
	filters: [["status", "=", "Active"]],

	// Left-most indicator
	get_indicator(doc) {
		const color_map = {
			Active: "green",
			Retired: "darkgrey",
		};
		return [__(doc.status), color_map[doc.status] || "blue", `status,=,${doc.status}`];
	},

	// Column-specific badges
	formatters: {
		group_based_on(value) {
			const color_map = {
				Cohort: "primary",   // blue
				Course: "info",      // teal
				Activity: "warning", // orange/yellow
				Other: "secondary",  // gray
			};
			const color = color_map[value] || "dark";
			return `<span class="badge bg-${color} text-white">${__(value)}</span>`;
		},
	},
};
