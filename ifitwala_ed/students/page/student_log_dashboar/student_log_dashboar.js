frappe.pages['student-log-dashboar'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Student Log Dashboard',
		single_column: true
	});
}