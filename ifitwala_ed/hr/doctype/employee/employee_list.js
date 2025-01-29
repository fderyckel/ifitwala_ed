// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Employee"] = {
	add_fields: ["status", "department", "designation", "employee_image"],
	filters: [["status", "=", "Active"]],
	get_indicator: function (doc) {
		var indicator = [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
		indicator[1] = { Active: "green", Inactive: "red", Left: "gray", Suspended: "orange" }[doc.status];
		return indicator;
	},
};