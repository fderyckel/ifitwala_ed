// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Term", {
	setup(frm) {
		frm.set_query("academic_year", function () {
			return {
				query: "ifitwala_ed.utilities.link_queries.academic_year_link_query",
				// pass school if already chosen; server falls back to user's default
				filters: { school: frm.doc.school || undefined },
			};
		});
	},

	refresh(frm) {},

	academic_year(frm) {
		if (!frm.doc.academic_year) return;
		frappe.db.get_value("Academic Year", frm.doc.academic_year, "school")
			.then(r => {
				const ay_school = r && r.message && r.message.school;
				if (ay_school && !frm.doc.school) {
					frm.set_value("school", ay_school);
				}
			});
	},

	term_start_date(frm) {
		if (frm.doc.term_start_date && !frm.doc.term_end_date) {
			const a_year_from_start = frappe.datetime.add_months(frm.doc.term_start_date);
			frm.set_value("term_end_date", frappe.datetime.add_days(a_year_from_start, -1));
		}
	},
});

