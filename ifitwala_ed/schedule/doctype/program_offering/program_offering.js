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
		freeze: false,
		callback: (r) => {
			const out = r && r.message ? r.message : {};
			if (!frm.doc.start_date && out.start_date) frm.set_value("start_date", out.start_date);
			if (!frm.doc.end_date && out.end_date) frm.set_value("end_date", out.end_date);
			if (!frm.doc.offering_title && out.offering_title) frm.set_value("offering_title", out.offering_title);
		}
	});
}

frappe.ui.form.on("Program Offering", {
	refresh(frm) {
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
