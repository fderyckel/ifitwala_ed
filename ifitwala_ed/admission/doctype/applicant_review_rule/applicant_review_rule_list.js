// Keep Applicant Review Rule list queries aligned with report view.
//
// Program Offering has show_title_field_in_link enabled, so Frappe adds a
// list-only joined field: program_offering.offering_title. That linked-title
// join is not needed for this configuration list and can make List view diverge
// from Report view under scoped permissions.

frappe.listview_settings["Applicant Review Rule"] = {
	onload(listview) {
		strip_program_offering_title_join(listview);
	},
	refresh(listview) {
		strip_program_offering_title_join(listview);
	},
};

function strip_program_offering_title_join(listview) {
	if (!listview || listview.__applicant_review_rule_title_join_stripped) return;

	const original_get_fields = listview.get_fields.bind(listview);
	listview.get_fields = function () {
		return original_get_fields().filter((field) => {
			return field !== "program_offering.offering_title as program_offering_offering_title";
		});
	};

	if (listview.link_field_title_fields) {
		delete listview.link_field_title_fields.program_offering;
	}

	listview.__applicant_review_rule_title_join_stripped = true;
}
