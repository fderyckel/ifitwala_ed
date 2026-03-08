// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.js

frappe.ui.form.on("Applicant Interview", {
	setup(frm) {
		frm.set_query("interviewer", "interviewers", () => ({
			query: "ifitwala_ed.api.users.get_users_with_role",
			filters: { role: "Employee" },
		}));
	},

	onload(frm) {
		if (!frm.is_new()) {
			return;
		}
		apply_new_interview_defaults(frm);
	},
});

function apply_new_interview_defaults(frm) {
	if (!frm.doc.interview_date) {
		frm.set_value("interview_date", frappe.datetime.get_today());
	}

	const user = String(frappe.session.user || "").trim();
	if (!user) {
		return;
	}

	const rows = Array.isArray(frm.doc.interviewers) ? frm.doc.interviewers : [];
	const hasCurrentUser = rows.some(row => String(row?.interviewer || "").trim() === user);
	if (hasCurrentUser) {
		return;
	}

	const row = frm.add_child("interviewers");
	row.interviewer = user;
	frm.refresh_field("interviewers");
}
