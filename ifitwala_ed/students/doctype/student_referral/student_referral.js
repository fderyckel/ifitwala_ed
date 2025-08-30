// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Referral", {
	onload(frm) {
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}
		frm.set_query("program_enrollment", () => {// ifitwala_ed/students/doctype/student_referral/student_referral.js

// ifitwala_ed/students/doctype/student_referral/student_referral.js
			return frm.doc.student ? { filters: { student: frm.doc.student } } : {};
		});
	},

	refresh(frm) {
		// Submitted: show Case actions
		if (frm.doc.docstatus === 1) {
			// View/Open Case
			if (frm.doc.referral_case) {
				frm.add_custom_button(__("View Case"), () => {
					frappe.set_route("Form", "Referral Case", frm.doc.referral_case);
				}, __("Actions"));
			} else {
				frm.add_custom_button(__("Open Case"), async () => {
					const r = await frm.call("open_case");
					if (r && r.message) {
						frm.reload_doc(); // picks up referral_case if server stamped it
						frappe.set_route("Form", "Referral Case", r.message);
					}
				}, __("Actions"));
			}

			// Escalate (works on the Case; submitted Referral is immutable)
			frm.add_custom_button(__("Escalate"), async () => {
				const case_name = await ensure_case(frm);
				if (!case_name) return;
				const d = new frappe.ui.Dialog({
					title: __("Escalate Case"),
					fields: [
						{ fieldname: "severity", fieldtype: "Select", label: __("Severity"), options: "High\nCritical", reqd: 1, default: "High" },
						{ fieldname: "note", fieldtype: "Small Text", label: __("Note (optional)") }
					],
					primary_action_label: __("Escalate"),
					primary_action: async (values) => {
						d.hide();
						await frappe.call({
							method: "ifitwala_ed.students.doctype.referral_case.referral_case.escalate",
							args: { name: case_name, severity: values.severity, note: values.note || "" }
						});
						frappe.show_alert({ message: __("Case escalated to {0}", [values.severity]), indicator: "red" });
						frappe.set_route("Form", "Referral Case", case_name);
					}
				});
				d.show();
			}, __("Actions"));

			// Mandated reporting marker (adds Case entry + bumps priority)
			frm.add_custom_button(__("Mark Mandated Reporting"), async () => {
				const case_name = await ensure_case(frm);
				if (!case_name) return;
				await frappe.call({
					method: "ifitwala_ed.students.doctype.referral_case.referral_case.flag_mandated_reporting",
					args: { name: case_name, referral: frm.doc.name }
				});
				frappe.msgprint({ title: __("Recorded"), message: __("Mandated reporting flagged on the case."), indicator: "red" });
			}, __("Actions"));
		}

		// Draft conveniences
		if (frm.doc.docstatus === 0) {
			// Autofill referrer for Staff
			if (frm.doc.referral_source === "Staff" && !frm.doc.referrer) {
				frm.set_value("referrer", frappe.session.user);
			}

			// Quick Escalate in draft (edits Referral fields before submit)
			frm.add_custom_button(__("Escalate (Draft)"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Escalate Referral"),
					fields: [
						{ fieldname: "severity", fieldtype: "Select", label: __("Severity"), options: "High\nCritical", reqd: 1, default: "High" },
						{ fieldname: "immediate", fieldtype: "Check", label: __("Requires Immediate Action"), default: 1 }
					],
					primary_action_label: __("Apply"),
					primary_action: () => {
						const v = d.get_values();
						d.hide();
						frm.set_value("severity", v.severity);
						frm.set_value("requires_immediate_action", v.immediate ? 1 : 0);
						frm.save();
					}
				});
				d.show();
			}, __("Actions"));

			// Quick Mandated toggle in draft (keeps server validation happy)
			frm.add_custom_button(__("Mandated Reporting (Draft)"), () => {
				frm.set_value("mandated_reporting_triggered", 1);
				if (!frm.doc.confidentiality_level || frm.doc.confidentiality_level === "Standard") {
					frm.set_value("confidentiality_level", "Sensitive");
				}
				if (!frm.doc.severity || frm.doc.severity === "Low") {
					frm.set_value("severity", "Moderate");
				}
				frm.save();
			}, __("Actions"));
		}
	},

	student: frappe.utils.debounce(async (frm) => {
		if (!frm.doc.student) return;
		const r = await frm.call("get_student_active_enrollment", {
			student: frm.doc.student,
			on_date: frm.doc.date || frappe.datetime.get_today()
		});
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
	}, 300),

	date: frappe.utils.debounce((frm) => {
		if (!frm.doc.student) return;
		frm.trigger("student");
	}, 300),

	program_enrollment(frm) {
		if (!frm.doc.program_enrollment) return;
		setTimeout(() => {
			if (!frm.doc.school && frm.doc.program) {
				frappe.db.get_value("Program", frm.doc.program, "school").then((r) => {
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
		frappe.db.get_value("Program", frm.doc.program, "school").then((r) => {
			if (r && r.message && r.message.school) {
				frm.set_value("school", r.message.school);
			}
		});
	}
}

async function ensure_case(frm) {
	if (frm.doc.referral_case) return frm.doc.referral_case;
	const r = await frm.call("open_case");
	return r && r.message ? r.message : null;
}
