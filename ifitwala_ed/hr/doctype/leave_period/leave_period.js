// ifitwala_ed/hr/doctype/leave_period/leave_period.js

frappe.ui.form.on("Leave Period", {
	from_date(frm) {
		if (frm.doc.from_date && !frm.doc.to_date) {
			const a_year_from_start = frappe.datetime.add_months(frm.doc.from_date, 12);
			frm.set_value("to_date", frappe.datetime.add_days(a_year_from_start, -1));
		}
	},
});
