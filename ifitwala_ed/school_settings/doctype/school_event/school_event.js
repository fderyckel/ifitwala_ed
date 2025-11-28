// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/school_settings/doctype/school_event/school_event.js

frappe.ui.form.on("School Event", {
	onload(frm) {
		set_reference_type_query(frm);
	},

	refresh(frm) {
		add_reference_jump_button(frm);
		toggle_participants_visibility(frm);
	},
});

// Child row event
frappe.ui.form.on("School Event Audience", {
	audience_type(frm, cdt, cdn) {
		toggle_participants_visibility(frm);
	},
});

function set_reference_type_query(frm) {
	if (!frm.fields_dict.reference_type) return;

	frm.set_query("reference_type", () => ({
		filters: { issingle: 0 },
	}));
}

function add_reference_jump_button(frm) {
	if (frm.is_new() || !frm.doc.reference_type || !frm.doc.reference_name) return;

	frm.add_custom_button(__(frm.doc.reference_name), () => {
		frappe.set_route("Form", frm.doc.reference_type, frm.doc.reference_name);
	});
}

// Show participants only for "Custom Users" audience rows
function toggle_participants_visibility(frm) {
	const rows = frm.doc.audience || [];
	const has_custom = rows.some(r => r.audience_type === "Custom Users");
	frm.toggle_display("participants", has_custom);
}
