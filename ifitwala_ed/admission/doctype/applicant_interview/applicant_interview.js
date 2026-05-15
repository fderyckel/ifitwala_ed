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

	refresh(frm) {
		add_my_feedback_action(frm);
	},

	validate(frm) {
		if (!frm.is_new()) {
			return;
		}
		if (frm.doc.school_event) {
			return;
		}
		frappe.validated = false;
		frappe.msgprint({
			title: __("Use Schedule Interview"),
			indicator: "orange",
			message: __(
				"New interviews must be scheduled from the Student Applicant or Admissions Cockpit so calendars and room availability are checked."
			),
		});
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

function add_my_feedback_action(frm) {
	frm.remove_custom_button(__("Open My Feedback"), __("Actions"));
	frm.remove_custom_button(__("Open My Feedback"));

	if (!frm.doc || frm.is_new()) {
		return;
	}

	const user = String(frappe.session.user || "").trim();
	if (!user || !is_current_user_interviewer(frm, user)) {
		return;
	}

	frm.add_custom_button(
		__("Open My Feedback"),
		() => open_my_feedback(frm, user),
		__("Actions")
	);
}

function is_current_user_interviewer(frm, user) {
	const rows = Array.isArray(frm.doc.interviewers) ? frm.doc.interviewers : [];
	return rows.some(row => String(row?.interviewer || "").trim() === user);
}

async function open_my_feedback(frm, user) {
	try {
		const { message } = await frappe.db.get_value(
			"Applicant Interview Feedback",
			{
				applicant_interview: frm.doc.name,
				interviewer_user: user,
			},
			"name"
		);

		const feedbackName = String(message?.name || "").trim();
		if (feedbackName) {
			frappe.set_route("Form", "Applicant Interview Feedback", feedbackName);
			return;
		}

		frappe.new_doc("Applicant Interview Feedback", {
			applicant_interview: frm.doc.name,
			student_applicant: frm.doc.student_applicant,
			interviewer_user: user,
			feedback_status: "Draft",
		});
	} catch (err) {
		frappe.msgprint(
			err?.message || __("Unable to open your interview feedback. Please try again or contact Admissions.")
		);
	}
}
