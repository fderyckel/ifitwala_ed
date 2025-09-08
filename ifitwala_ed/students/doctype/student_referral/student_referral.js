// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Referral", {
	onload(frm) {
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}
		// Only show unarchived PEs for the chosen student
		frm.set_query("program_enrollment", () => {
			return frm.doc.student
				? { filters: { student: frm.doc.student, archived: 0 } }
				: {};
		});
	},

	refresh(frm) {
		// avoid duplicated buttons across refreshes
		frm.clear_custom_buttons();

		// Submitted actions: Counselor/Admin only; authoritative actions live on the Case
		const canReadCase =
			((frappe.boot.user && frappe.boot.user.can_read) || []).includes("Referral Case");
		const canCaseUI =
			frm.doc.docstatus === 1 &&
			frappe.user.has_role(["Counselor", "Academic Admin"]) &&
			canReadCase;

		if (canCaseUI) {
			// View/Open Case only (no authoritative actions here)
			if (frm.doc.referral_case) {
				const viewBtn = frm.add_custom_button(__("View Case"), () => {
					frappe.set_route("Form", "Referral Case", frm.doc.referral_case);
				});
				viewBtn.addClass("btn-success");
			} else {
				const openBtn = frm.add_custom_button(__("Open Case"), async () => {
					const r = await frm.call("open_case");
					if (r && r.message) {
						await frm.reload_doc();
						frappe.set_route("Form", "Referral Case", r.message);
					}
				});
				openBtn.addClass("btn-primary");
			}

			frm.dashboard.set_headline(__(
				"Authoritative triage (<b>Escalate</b> & <b>Mandated Reporting</b>) is performed on the <b>Referral Case</b>."
			));
		}

		// --- Intake-side non-authoritative actions ---
		// Show ONLY to Academic Staff (not Counselors/Admins), and ONLY on Submitted referrals
		const isAcademicStaff = frappe.user.has_role("Academic Staff");
		const hasTriageRole = frappe.user.has_role(["Counselor", "Academic Admin"]);

		if (frm.doc.docstatus === 1 && isAcademicStaff && !hasTriageRole) {
			// Request Escalation
			const reqBtn = frm.add_custom_button(__("Request Escalation"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Request Escalation"),
					fields: [
						{ fieldname: "note", fieldtype: "Small Text", label: __("Add context (optional)") }
					],
					primary_action_label: __("Send Request"),
					primary_action: async (values) => {
						d.hide();
						await frappe.call({
							method: "ifitwala_ed.students.doctype.student_referral.student_referral.request_escalation",
							args: { referral: frm.doc.name, note: values.note || "" }
						}).then((r) => {
							const banner = (r && r.message && r.message.banner) || __("Escalation request recorded.");
							frm.dashboard.set_headline(`<span class="text-warning">${frappe.utils.escape_html(banner)}</span>`);
							frappe.show_alert({ message: __("Triage team notified."), indicator: "orange" });
							frm.reload_doc(); // pull timeline
						});
					}
				});
				d.show();
			});
			reqBtn.addClass("btn-warning");

			// Mark Possible MR (non-authoritative)
			const mrFlagBtn = frm.add_custom_button(__("Possible Mandatory Reporting"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Flag Possible Mandated Report"),
					fields: [
						{ fieldname: "note", fieldtype: "Small Text", label: __("Why do you suspect this? (optional)") }
					],
					primary_action_label: __("Flag"),
					primary_action: async (values) => {
						d.hide();
						await frappe.call({
							method: "ifitwala_ed.students.doctype.student_referral.student_referral.flag_possible_mandated_report",
							args: { referral: frm.doc.name, note: values.note || "" }
						}).then((r) => {
							const banner = (r && r.message && r.message.banner) || __("Flag recorded.");
							frm.dashboard.set_headline(`<span class="text-danger">${frappe.utils.escape_html(banner)}</span>`);
							frappe.show_alert({ message: __("Triage team notified."), indicator: "red" });
							frm.reload_doc();
						});
					}
				});
				d.show();
			});
			mrFlagBtn.addClass("btn-danger");
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

