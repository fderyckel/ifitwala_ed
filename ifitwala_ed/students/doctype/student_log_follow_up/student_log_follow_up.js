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

	// ✅ Complete button should only be visible when:
	// - this follow-up is submitted (docstatus = 1), AND
	// - current user is the PARENT Student Log author (owner) OR has role "Academic Admin".
	const isAdmin = frappe.user.has_role("Academic Admin");

	// Helper to add the button if allowed
	const maybe_add_complete_btn = (parentOwner) => {
		const canComplete =
			frm.doc.docstatus === 1 &&
			(isAdmin || (parentOwner && parentOwner === frappe.session.user));

		if (!canComplete) return;

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
	};

	// Fetch parent owner only once per form load / parent value (memoized)
	if (frm.doc.student_log) {
		if (frm._parent_owner_for === frm.doc.student_log && frm._parent_owner_user) {
			maybe_add_complete_btn(frm._parent_owner_user);
		} else {
			frappe.db.get_value("Student Log", frm.doc.student_log, "owner").then(r => {
				const parentOwner = (r && r.message && r.message.owner) ? r.message.owner : null;
				// memoize
				frm._parent_owner_for = frm.doc.student_log;
				frm._parent_owner_user = parentOwner;
				maybe_add_complete_btn(parentOwner);
			});
		}
	}
}

});
