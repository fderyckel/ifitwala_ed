// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

// ifitwala_ed/setup/doctype/organization/organization.js

function clear_invalid_default_school(frm, school, school_org) {
	frappe.msgprint(
		__(
			"Default Website School must belong to this Organization. " +
			"School '{0}' belongs to '{1}', not '{2}'.",
			[school, school_org || __("Unknown"), frm.doc.name || __("this Organization")]
		)
	);
	frm.set_value("default_website_school", null);
}

frappe.ui.form.on("Organization", {
	setup(frm) {
		frm.set_query("default_website_school", () => {
			const filters = {};
			if (frm.doc.name && !frm.is_new()) {
				filters.organization = frm.doc.name;
			}
			return { filters };
		});
	},

	default_website_school(frm) {
		const school = frm.doc.default_website_school;
		if (!school || !frm.doc.name || frm.is_new()) {
			return;
		}

		frappe.db.get_value("School", school, "organization", (r) => {
			const school_org = r && r.organization;
			if (!school_org || school_org !== frm.doc.name) {
				clear_invalid_default_school(frm, school, school_org);
			}
		});
	},
});
