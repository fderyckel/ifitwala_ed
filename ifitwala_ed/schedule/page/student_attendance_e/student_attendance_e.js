frappe.pages['student-attendance-e'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Student Attendance Tool',
		single_column: true
	});
}