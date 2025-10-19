// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/program/program.js

frappe.ui.form.on("Program", {
	onload(frm) {
		// Filter the child "course" link in the "courses" table
		frm.set_query("course", "courses", function (doc, cdt, cdn) {
			const picked = (doc.courses || [])
				.filter(r => r.course)
				.map(r => r.course);

			return {
				filters: [
					["Course", "name", "not in", picked],   // no duplicates
					["Course", "status", "=", "Active"]     // only Active
				]
			};
		});
	},

	onload_post_render(frm) {
		// keep your multiple add UX
		frm.get_field("courses").grid.set_multiple_add("course");
	}
});

// to filter out courses that have already been picked out in the program.
frappe.ui.form.on("Program Course", {
});
