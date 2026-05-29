// Keep Program Enrollment Request List view aligned with Report view.
//
// Frappe v16 adds title joins for Link fields whose targets have
// show_title_field_in_link enabled. Program Offering and Student have scoped
// permission query hooks, and the generated join aliases can make List view
// reference target tables by their unaliased names.

frappe.listview_settings["Program Enrollment Request"] = {
	onload(listview) {
		strip_program_enrollment_request_title_joins(listview);
	},
	refresh(listview) {
		strip_program_enrollment_request_title_joins(listview);
	},
};

function strip_program_enrollment_request_title_joins(listview) {
	if (!listview || listview.__program_enrollment_request_title_joins_stripped) return;

	const blocked_fields = new Set([
		"program_offering.offering_title as program_offering_offering_title",
		"student.student_full_name as student_student_full_name",
	]);
	const original_get_fields = listview.get_fields.bind(listview);
	listview.get_fields = function () {
		return original_get_fields().filter((field) => !blocked_fields.has(field));
	};

	if (listview.link_field_title_fields) {
		delete listview.link_field_title_fields.program_offering;
		delete listview.link_field_title_fields.student;
	}

	listview.__program_enrollment_request_title_joins_stripped = true;
}
