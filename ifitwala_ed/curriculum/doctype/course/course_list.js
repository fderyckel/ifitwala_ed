// Copyright (c) 2020, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Course'] = {
	filters: [["status","=", "Active"]],
	hide_name_column: true, 
	get_indicator: function(doc) {
		var indicator = [__(doc.status), frappe.utils.guess_colour(doc.status), "status,=," + doc.status];
		indicator[1] = {"Active": "green", "Discontinued": "darkgrey"}[doc.status];
		return indicator;
	}
};