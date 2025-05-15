// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Academic Year"] = {
	hide_name_column: true,
	add_fields: ["title", "school", "year_start_date", "year_end_date", "archived"],
	onload: function(listview) {
		// Apply horizontal scroll to the list view
		listview.page.wrapper.find('.frappe-list').css({
			'overflow-x': 'auto',
			'white-space': 'nowrap'
		});
	}
};
