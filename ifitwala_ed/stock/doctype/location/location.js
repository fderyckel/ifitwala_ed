// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

// ifitwala_ed/stock/doctype/location/location.js

frappe.ui.form.on("Location", {
	setup(frm) {
		// Parent Location: only groups, and (if set) same organization
		frm.set_query("parent_location", () => {
			return {
				query: "ifitwala_ed.stock.doctype.location.location.get_valid_parent_locations",
				filters: {
					organization: frm.doc.organization || null,
					school: frm.doc.school || null
				}
			};
		});

		// School: constrained by organization when present
		frm.set_query("school", () => {
			const filters = {};
			if (frm.doc.organization) {
				// Only schools that belong to this organization
				filters.organization = frm.doc.organization;
			}
			return { filters };
		});
	},

	onload(frm) {
		// If new and parent is set but org is empty, copy from parent for UX
		if (frm.is_new() && frm.doc.parent_location && !frm.doc.organization) {
			copy_parent_org(frm);
		}
	},

	parent_location(frm) {
		// When parent changes, align organization from parent
		if (frm.doc.parent_location) {
			copy_parent_org(frm);
		}
	},

	school(frm) {
		// When user selects a school:
		// - if organization is empty, auto-fill from school
		// - if organization is set and does not match, warn + clear school
		if (!frm.doc.school) {
			return;
		}

		frappe.db
			.get_value("School", frm.doc.school, "organization")
			.then(r => {
				const school_org = r?.message?.organization || null;

				// No org on school → let server-side validation scream
				if (!school_org) {
					frappe.msgprint({
						title: __("School Missing Organization"),
						message: __(
							"Selected School {0} has no Organization set. "
							+ "Please fix the School configuration.",
							[frm.doc.school]
						),
						indicator: "orange"
					});
					return;
				}

				// If Location.organization is empty, auto-fill it
				if (!frm.doc.organization) {
					frm.set_value("organization", school_org);
					return;
				}

				// If org is already set and doesn't match the school's org, block this choice
				if (frm.doc.organization !== school_org) {
					frappe.msgprint({
						title: __("School Does Not Belong to Organization"),
						message: __(
							"The selected School belongs to Organization {0}, "
							+ "which does not match this Location's Organization {1}.",
							[school_org, frm.doc.organization]
						),
						indicator: "red"
					});
					frm.set_value("school", null);
				}
			});
	},

	organization(frm) {
		// Existing behavior: enforce parent_location org alignment
		if (frm.doc.parent_location && frm.doc.organization) {
			frappe.db
				.get_value("Location", frm.doc.parent_location, "organization")
				.then(r => {
					const parent_org = r?.message?.organization;
					if (parent_org && parent_org !== frm.doc.organization) {
						frappe.msgprint({
							title: __("Organization will be forced to match parent"),
							message: __(
								"Parent Organization is {0}. This Location must use the same Organization.",
								[parent_org]
							),
							indicator: "orange"
						});
						frm.set_value("organization", parent_org);
					}
				});
		}

		// NEW: if org changed and current school doesn't belong to it, clear school
		if (frm.doc.school && frm.doc.organization) {
			frappe.db
				.get_value("School", frm.doc.school, "organization")
				.then(r => {
					const school_org = r?.message?.organization || null;
					if (!school_org) {
						// Let server-side handle misconfig, but we can warn
						frappe.msgprint({
							title: __("School Missing Organization"),
							message: __(
								"Selected School {0} has no Organization set. "
								+ "Please fix the School configuration.",
								[frm.doc.school]
							),
							indicator: "orange"
						});
						return;
					}

					if (school_org !== frm.doc.organization) {
						frappe.msgprint({
							title: __("School Cleared Due to Organization Change"),
							message: __(
								"The selected School belongs to Organization {0}, "
								+ "which no longer matches this Location's Organization {1}. "
								+ "The School field has been cleared.",
								[school_org, frm.doc.organization]
							),
							indicator: "orange"
						});
						frm.set_value("school", null);
					}
				});
		}
	}
});

function copy_parent_org(frm) {
	if (!frm.doc.parent_location) return;

	frappe.db
		.get_value("Location", frm.doc.parent_location, "organization")
		.then(r => {
			const parent_org = r?.message?.organization;
			if (parent_org && frm.doc.organization !== parent_org) {
				frm.set_value("organization", parent_org);
			}
		});
}
