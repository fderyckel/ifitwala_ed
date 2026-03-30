// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/instructor/instructor.js

frappe.ui.form.on("Instructor", {
	onload(frm) {
		frm.set_query("employee", () => ({
			query: "ifitwala_ed.schedule.doctype.instructor.instructor.instructor_employee_query",
			filters: {
				current_instructor: frm.doc.name || "",
				current_employee: frm.doc.employee || "",
			},
		}));
	},

});
