// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Student Group"] = {
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
				Cohort: "primary",
				Course: "purple",
				Activity: "orange",
				Other: "secondary",
			};
			const color = color_map[value] || "dark";
			return `<span class="badge bg-${color} text-white">${__(value)}</span>`;
		},
	},
};
