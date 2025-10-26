// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

// ifitwala_ed/stock/doctype/location/location.js

frappe.ui.form.on("Location", {
	setup(frm) {
		frm.set_query("parent_location", () => {
			const filters = { is_group: 1 };
			if (frm.doc.organization) filters.organization = frm.doc.organization;
			return { filters };
		});
	},

	onload(frm) {
		if (frm.is_new() && frm.doc.parent_location && !frm.doc.organization) {
			copy_parent_org(frm);
		}
	},

	parent_location(frm) {
		if (frm.doc.parent_location) copy_parent_org(frm);
	},

	organization(frm) {
		if (frm.doc.parent_location && frm.doc.organization) {
			frappe.db.get_value("Location", frm.doc.parent_location, "organization").then(r => {
				const parent_org = r?.message?.organization;
				if (parent_org && parent_org !== frm.doc.organization) {
					frappe.msgprint({
						title: __("Organization will be forced to match parent"),
						message: __("Parent Organization is {0}. This Location must use the same Organization.", [parent_org]),
						indicator: "orange"
					});
					frm.set_value("organization", parent_org);
				}
			});
		}
	}
});

function copy_parent_org(frm) {
	frappe.db.get_value("Location", frm.doc.parent_location, "organization").then(r => {
		const parent_org = r?.message?.organization;
		if (parent_org && frm.doc.organization !== parent_org) {
			frm.set_value("organization", parent_org);
		}
	});
}
