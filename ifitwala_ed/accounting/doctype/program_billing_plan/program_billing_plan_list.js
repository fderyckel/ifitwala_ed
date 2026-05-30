// Keep Program Billing Plan List view aligned with Report view.
//
// Frappe v16 adds a title join for Program Offering because that target DocType
// has show_title_field_in_link enabled. The joined title is cosmetic here, while
// the target DocType's scoped permission condition can make List view reference
// the target table by its unaliased name.

frappe.listview_settings['Program Billing Plan'] = {
	onload(listview) {
		strip_program_billing_plan_title_joins(listview);
	},
	refresh(listview) {
		strip_program_billing_plan_title_joins(listview);
	},
};

function strip_program_billing_plan_title_joins(listview) {
	if (!listview || listview.__program_billing_plan_title_joins_stripped) return;

	const blocked_fields = new Set([
		'program_offering.offering_title as program_offering_offering_title',
	]);
	const original_get_fields = listview.get_fields.bind(listview);
	listview.get_fields = function () {
		return original_get_fields().filter(field => !blocked_fields.has(field));
	};

	if (listview.link_field_title_fields) {
		delete listview.link_field_title_fields.program_offering;
	}

	listview.__program_billing_plan_title_joins_stripped = true;
}
