// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

function apply_server_defaults_if_empty(frm) {
	if (!frm.doc.program || !frm.doc.school) return;

	const ayNames = (frm.doc.offering_academic_years || [])
		.map(r => r.academic_year)
		.filter(Boolean);

	if (!ayNames.length) return;

	frappe.call({
		method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.compute_program_offering_defaults",
		args: {
			program: frm.doc.program,
			school: frm.doc.school,
			ay_names: JSON.stringify(ayNames)
		},
		callback: (r) => {
			const out = (r && r.message) || {};
			if (!frm.doc.start_date && out.start_date) frm.set_value("start_date", out.start_date);
			if (!frm.doc.end_date && out.end_date) frm.set_value("end_date", out.end_date);
			if (!frm.doc.offering_title && out.offering_title) frm.set_value("offering_title", out.offering_title);
		}
	});
}

/* ---------------- Helpers for default span ---------------- */
function first_and_last_ay(frm) {
	const ays = (frm.doc.offering_academic_years || []).map(r => r.academic_year).filter(Boolean);
	return { first: ays.length ? ays[0] : null, last: ays.length ? ays[ays.length - 1] : null };
}

function insert_offering_course_rows(frm, rows) {
	const span = first_and_last_ay(frm);
	(rows || []).forEach(r => {
		const child = frm.add_child("offering_courses");
		child.course = r.course;
		child.course_name = r.course_name || r.course;
		child.required = r.required ? 1 : 0;
		child.elective_group = r.elective_group || "";
		if ("non_catalog" in r) child.non_catalog = r.non_catalog ? 1 : 0;
		if ("exception_reason" in r) child.exception_reason = r.exception_reason || "";
		if ("catalog_ref" in r) child.catalog_ref = r.catalog_ref || "";

		// Default full span to offering AY envelope
		if (span.first) child.start_academic_year = span.first;
		if (span.last)  child.end_academic_year = span.last;
	});
	frm.refresh_field("offering_courses");
}

/* ---------------- Catalog Picker ---------------- */
function open_catalog_picker(frm) {
	if (!frm.doc.program) {
		frappe.msgprint(__("Pick a Program first."));
		return;
	}

	// Get catalog options (server resolves Program Course / fallback)
	frappe.call({
		method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.program_course_options",
		args: { program: frm.doc.program },
		callback: (r) => {
			const catalog = (r && r.message) || [];
			if (!catalog.length) {
				frappe.msgprint(__("No catalog courses found for this Program."));
				return;
			}
			const allowed = catalog.map(x => x.course);

			new frappe.ui.form.MultiSelectDialog({
				doctype: "Course",
				target: frm,
				size: "large",
				// Filter dialog list to the catalog courses
				get_query: () => ({ filters: { name: ["in", allowed] } }),
				primary_action_label: __("Add from Catalog"),
				action: (selections) => {
					if (!selections || !selections.length) return;

					frappe.call({
						method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.hydrate_catalog_rows",
						args: {
							program: frm.doc.program,
							course_names: JSON.stringify(selections)
						},
						callback: (rr) => {
							insert_offering_course_rows(frm, (rr && rr.message) || []);
						}
					});
				}
			});
		}
	});
}

/* ---------------- Non-catalog Picker ---------------- */
function open_non_catalog_picker(frm) {
	if (!frm.doc.program) {
		frappe.msgprint(__("Pick a Program first."));
		return;
	}

	// First ask for justification, then open course picker
	frappe.prompt(
		[
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason / Justification"),
				reqd: 1
			}
		],
		(values) => {
			const reason = (values && values.reason) || "";
			new frappe.ui.form.MultiSelectDialog({
				doctype: "Course",
				target: frm,
				size: "large",
				primary_action_label: __("Add Non-catalog"),
				action: (selections) => {
					if (!selections || !selections.length) return;

					frappe.call({
						method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.hydrate_non_catalog_rows",
						args: {
							course_names: JSON.stringify(selections),
							exception_reason: reason
						},
						callback: (rr) => {
							insert_offering_course_rows(frm, (rr && rr.message) || []);
						}
					});
				}
			});
		},
		__("Non-catalog Course"),
		__("Continue")
	);
}

frappe.ui.form.on("Program Offering", {
	refresh(frm) {
		// Place buttons under a "Courses" group
		const btnCatalog = frm.add_custom_button(__("Add from Catalog"), () => open_catalog_picker(frm));
		if (btnCatalog) btnCatalog.addClass("btn-primary"); // blue

		const btnNonCat = frm.add_custom_button(__("Add Non-catalog"), () => open_non_catalog_picker(frm));
		if (btnNonCat) btnNonCat.addClass("btn-secondary");

		apply_server_defaults_if_empty(frm);
	},

	program(frm) {
		apply_server_defaults_if_empty(frm);
	},
	
	school(frm) {
		apply_server_defaults_if_empty(frm);
	}
});

frappe.ui.form.on("Program Offering Academic Year", {
	academic_year(frm) {
		apply_server_defaults_if_empty(frm);
	}
});
