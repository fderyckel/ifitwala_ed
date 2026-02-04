// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Employee"] = {
	add_fields: ["employment_status", "department", "designation", "employee_image"],
	filters: [["employment_status", "=", "Active"]],
	get_indicator: function (doc) {
		var indicator = [
			__(doc.employment_status),
			frappe.utils.guess_colour(doc.employment_status),
			"employment_status,=," + doc.employment_status,
		];
		indicator[1] = { Active: "green", Inactive: "red", Left: "gray", Suspended: "orange" }[
			doc.employment_status
		];
		return indicator;
	},
};
