frappe.pages['school_schedule_calendar'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'School Schedule Calendar',
		single_column: true
	});
}