// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/doctype/student_referral/student_referral.js

frappe.ui.form.on("Student Referral", {
	onload: function (frm) {
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}
		frm.set_query("program_enrollment", function () {
			return frm.doc.student ? { filters: { student: frm.doc.student } } : {};
		});
	},

	refresh: function (frm) {
		// Add Open Case button on submitted referrals
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Open Case"), async function () {
				const r = await frm.call("open_case");
				if (r && r.message) {
					frappe.set_route("Form", "Referral Case", r.message);
				}
			}, __("Actions"));
		}

		// Autofill referrer for Staff
		if (frm.doc.referral_source === "Staff" && !frm.doc.referrer && frm.doc.docstatus === 0) {
			frm.set_value("referrer", frappe.session.user);
		}
	},

	student: frappe.utils.debounce(function (frm) {
		if (!frm.doc.student) return;

		frm.call("get_student_active_enrollment", {
			student: frm.doc.student,
			on_date: frm.doc.date || frappe.datetime.get_today()
		}).then(r => {
			const msg = r && r.message;

			if (!msg || (Array.isArray(msg) && msg.length === 0)) {
				frappe.msgprint({
					title: __("No Program Enrollment"),
					message: __("No active or recent program enrollment found for this student."),
					indicator: "orange"
				});
				frm.set_value("program_enrollment", null);
				frm.set_value("program", null);
				frm.set_value("academic_year", null);
				frm.set_value("school", null);
				return;
			}

			if (Array.isArray(msg) && msg.length > 1) {
				const lines = msg.map(pe =>
					`${pe.name} • ${pe.program || "—"} • ${pe.academic_year || "—"} • ${pe.school || "—"}`
				).join("\n");

				const d = new frappe.ui.Dialog({
					title: __("Select Program Enrollment"),
					fields: [{
						fieldname: "pe_label",
						label: __("Program Enrollment"),
						fieldtype: "Select",
						options: lines,
						reqd: 1
					}],
					primary_action_label: __("Use"),
					primary_action: () => {
						const label = d.get_value("pe_label");
						const hit = msg.find(pe =>
							`${pe.name} • ${pe.program || "—"} • ${pe.academic_year || "—"} • ${pe.school || "—"}` === label
						);
						if (hit) apply_enrollment(frm, hit);
						d.hide();
					}
				});
				d.show();
				return;
			}

			apply_enrollment(frm, Array.isArray(msg) ? msg[0] : msg);
			frm.trigger("program_enrollment");
		});
	}, 300),

	date: frappe.utils.debounce(function (frm) {
		if (!frm.doc.student) return;
		frm.trigger("student");
	}, 300),

	program_enrollment: function (frm) {
		if (!frm.doc.program_enrollment) return;
		setTimeout(function () {
			if (!frm.doc.school && frm.doc.program) {
				frappe.db.get_value("Program", frm.doc.program, "school").then(function (r) {
					if (r && r.message && r.message.school) {
						frm.set_value("school", r.message.school);
					}
				});
			}
		}, 150);
	}
});

function apply_enrollment(frm, pe) {
	frm.set_value("program_enrollment", pe.name);
	if (pe.school) {
		frm.set_value("school", pe.school);
	} else if (frm.doc.program) {
		frappe.db.get_value("Program", frm.doc.program, "school").then(function (r) {
			if (r && r.message && r.message.school) {
				frm.set_value("school", r.message.school);
			}
		});
	}
}
