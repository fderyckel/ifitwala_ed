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

	async refresh(frm) {
		if (frm.is_new() || frm.__instructor_log_sync_in_flight) {
			return;
		}

		frm.__instructor_log_sync_in_flight = true;
		try {
			const { message } = await frappe.call({
				method: "ifitwala_ed.schedule.doctype.instructor.instructor.get_instructor_log",
				args: { instructor: frm.doc.name },
			});

			if (message?.changed) {
				await frm.reload_doc();
			}
		} finally {
			frm.__instructor_log_sync_in_flight = false;
		}
	},

});
