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

		// ✅ Complete button should be visible when:
		// - this follow-up is submitted (docstatus = 1), AND
		// - current user is: PARENT author (owner) OR has role "Academic Admin" OR is the current OPEN assignee on the parent.
		const isAdmin = frappe.user.has_role("Academic Admin");

		const maybe_add_complete_btn = (parentOwner, currentAssignee) => {
			const isParentOwner = !!parentOwner && parentOwner === frappe.session.user;
			const isCurrentAssignee = !!currentAssignee && currentAssignee === frappe.session.user;

			const canComplete =
				frm.doc.docstatus === 1 &&
				(isAdmin || isParentOwner || isCurrentAssignee);

			if (!canComplete) return;

			const cbtn = frm.add_custom_button(__("✅ Complete Parent Log"), () => {
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

		// Fetch parent owner + current OPEN assignee (memoized per parent)
		if (frm.doc.student_log) {
			const useMemo = frm._perm_cache_for === frm.doc.student_log && frm._perm_cache;
			if (useMemo) {
				maybe_add_complete_btn(frm._perm_cache.owner, frm._perm_cache.assignee);
			} else {
				Promise.all([
					frappe.db.get_value("Student Log", frm.doc.student_log, "owner"),
					frappe.db.get_value("ToDo", {
						reference_type: "Student Log",
						reference_name: frm.doc.student_log,
						status: "Open"
					}, "allocated_to")
				]).then(([ownerRes, todoRes]) => {
					const owner = ownerRes?.message?.owner || null;
					const assignee = todoRes?.message?.allocated_to || null;

					// memoize
					frm._perm_cache_for = frm.doc.student_log;
					frm._perm_cache = { owner, assignee };

					maybe_add_complete_btn(owner, assignee);
				});
			}
		}
	}
});
