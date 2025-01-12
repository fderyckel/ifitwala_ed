frappe.pages['stud_portal'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Student Portal',
		single_column: true
	});
}