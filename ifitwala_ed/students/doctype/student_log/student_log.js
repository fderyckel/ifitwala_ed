// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Log", {
	onload(frm) {
		// keep original student filter
		frm.set_query("student", () => ({ filters: { enabled: 1 } }));

		// mirror field should be read-only in UI (assignments drive it)
		frm.set_df_property("follow_up_person", "read_only", 1); // NEW

		if (frm.is_new()) {
			if (!frm.doc.date) frm.set_value("date", frappe.datetime.get_today());
			if (!frm.doc.time) frm.set_value("time", frappe.datetime.now_time());

			if (!frm.doc.author_name) {
				frappe.call({
					method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
					callback(r) {
						if (r && r.message && r.message.employee_full_name) {
							frm.set_value("author_name", r.message.employee_full_name);
						}
					}
				});
			}
		}
	},

	refresh(frm) {
		const is_author = frappe.session.user_fullname === frm.doc.author_name;
		const status = (frm.doc.follow_up_status || "").toLowerCase();

		// Assign / Reassign follow-up (native assignment) — only when follow-up is required
		if (frm.doc.requires_follow_up) { // NEW
			frm.add_custom_button(__("Assign Follow-Up"), () => {
				if (frm.is_dirty()) {
					frappe.msgprint(__("Please save the document before assigning."));
					return;
				}
				const role = frm.doc.follow_up_role || "Academic Staff";
				const d = new frappe.ui.Dialog({
					title: __("Assign Follow-Up"),
					fields: [
						{
							fieldname: "user",
							fieldtype: "Link",
							label: __("User"),
							options: "User",
							reqd: 1,
							get_query: () => ({
								query: "ifitwala_ed.api.get_users_with_role",
								filters: { role }
							})
						}
					],
					primary_action_label: __("Assign"),
					primary_action(values) {
						d.hide();
						frappe.call({
							method: "ifitwala_ed.students.doctype.student_log.student_log.assign_follow_up",
							args: { log_name: frm.doc.name, user: values.user },
							callback: () => frm.reload_doc()
						});
					}
				});
				d.show();
			}, __("Actions"));
		}

		// New Follow-Up (unchanged)
		if (status !== "completed") {
			frm.add_custom_button(__("New Follow-Up"), () => {
				frappe.call({
					method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
					callback(r) {
						frappe.new_doc("Student Log Follow Up", {
							student_log: frm.doc.name,
							follow_up_author: r.message?.employee_full_name || "",
							date: frappe.datetime.get_today()
						});
					}
				});
			});
		}

		// Mark as Completed (unchanged)
		if (status === "closed" && is_author) {
			frm.add_custom_button(__("Mark as Completed"), () => {
				frm.call({
					method: "frappe.client.set_value",
					args: {
						doctype: "Student Log",
						name: frm.doc.name,
						fieldname: "follow_up_status",
						value: "Completed"
					},
					callback() {
						frappe.show_alert({ message: __("Marked as Completed"), indicator: "green" });
						frm.reload_doc();
					}
				});
			}, __("Actions"));
		}

		// Finalize: Close (unchanged)
		if (frm.doc.follow_up_status === "Completed" && frappe.user.has_role("Academic Admin")) {
			frm.add_custom_button(__("Finalize: Close Log"), () => {
				frappe.call({
					method: "frappe.client.set_value",
					args: {
						doctype: "Student Log",
						name: frm.doc.name,
						fieldname: "follow_up_status",
						value: "Closed"
					},
					callback() {
						frappe.show_alert({ message: __("Log finalized and closed"), indicator: "red" });
						frm.reload_doc();
					}
				});
			}, __("Actions"));
		}
	},

	student(frm) {
		if (!frm.doc.student) {
			frm.set_value("program", "");
			frm.set_value("academic_year", "");
			return;
		}

		frappe.call({
			method: "ifitwala_ed.students.doctype.student_log.student_log.get_active_program_enrollment",
			args: { student: frm.doc.student },
			callback(r) {
				if (r && r.message) {
					frm.set_value("program", r.message.program || "");
					frm.set_value("academic_year", r.message.academic_year || "");
				} else {
					console.warn("No active enrollment returned", r);
					frappe.msgprint({ message: __("No active Program Enrollment found for this student."), indicator: "orange" });
				}
			},
			error(err) { console.error("Error in get_active_program_enrollment", err); }
		});
	},

	author(frm) {
		// Keep original behavior
		if (frm.doc.author) {
			frappe.call({
				method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
				args: { employee_name: frm.doc.author },
				callback(r) {
					if (r && r.message && r.message.name) {
						frm.set_value("author_name", r.message.employee_full_name);
					} else {
						frm.set_value("author_name", "");
					}
				}
			});
		} else {
			frm.set_value("author_name", "");
		}
	},

	next_step(frm) {
		if (!frm.doc.next_step) return;

		frappe.call({
			method: "ifitwala_ed.students.doctype.student_log.student_log.get_follow_up_role_from_next_step",
			args: { next_step: frm.doc.next_step },
			callback(r) {
				const role = r.message || "Academic Staff";
				frm.set_value("follow_up_role", role);
				// NOTE: follow_up_person remains read-only; role filters the Assign dialog instead.
			}
		});
	},

	requires_follow_up(frm) {
		const show = frm.doc.requires_follow_up === 1;
		frm.toggle_display(["next_step", "follow_up_role", "follow_up_person", "follow_up_status"], show);

		// Mapping: when turned off, status must be blank (server enforces)
		if (!show) {
			frm.set_value("follow_up_status", null); // CHANGED (was "Closed")
		} else if (!frm.doc.follow_up_status || frm.doc.follow_up_status === "Closed") {
			frm.set_value("follow_up_status", "Open");
		}
	}
});

// Realtime toast for the author when a follow-up is submitted (kept)
frappe.realtime.on("follow_up_ready_to_review", function (data) {
	frappe.show_alert({
		message: __("A follow-up for {0} is now ready for your review.", [data.student_name || data.log_name]),
		indicator: "green"
	});
});