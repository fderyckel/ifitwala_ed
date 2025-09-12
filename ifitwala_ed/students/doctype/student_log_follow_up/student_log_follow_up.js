// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Log Follow Up", {
	onload(frm) {
		// Set follow_up_author once (mirror current user full name)
		if (!frm.doc.follow_up_author) {
			frappe.call({
				method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
				callback(r) {
					if (r && r.message && r.message.employee_full_name) {
						frm.set_value("follow_up_author", r.message.employee_full_name);
					}
				}
			});
		}

		// Ensure date exists
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}
	},

	refresh(frm) {
		// Avoid duplicate buttons on rerender
		frm.clear_custom_buttons();

		// Safety: if author still blank (rare), fill once
		if (!frm.doc.follow_up_author) {
			frappe.call({
				method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
				callback(r) {
					if (r && r.message && r.message.employee_full_name) {
						frm.set_value("follow_up_author", r.message.employee_full_name);
					}
				}
			});
		}

		// Ensure date exists
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}

		// Quick navigation to parent Student Log
		if (frm.doc.student_log) {
			frm.add_custom_button(__("Open Student Log"), () => {
				frappe.set_route("Form", "Student Log", frm.doc.student_log);
			});
		}

		// ✅ Complete button (visible only when submitted + (author OR Academic Admin))
		const isOwner = frm.doc.owner === frappe.session.user;
		const isAdmin = frappe.user.has_role("Academic Admin");
		if (frm.doc.docstatus === 1 && (isOwner || isAdmin)) {
			const cbtn = frm.add_custom_button(__("✅ Complete"), () => {
				frappe.call({
					method: "ifitwala_ed.students.doctype.student_log.student_log.complete_follow_up",
					args: { follow_up_name: frm.doc.name },
					callback() {
						frappe.show_alert({ message: __("Follow-up marked completed."), indicator: "green" });
						if (frm.doc.student_log) {
							frappe.set_route("Form", "Student Log", frm.doc.student_log);
						} else {
							frm.reload_doc();
						}
					}
				});
			});
			cbtn.addClass("btn-success");
		}
	}

});
