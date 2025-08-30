// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Log", {
	onload(frm) {
		// 1) Only enabled students selectable
		frm.set_query("student", () => ({ filters: { enabled: 1 } }));

		// 2) Soft defaults on new docs
		if (frm.is_new()) {
			if (!frm.doc.date) frm.set_value("date", frappe.datetime.get_today());
			if (!frm.doc.time) frm.set_value("time", frappe.datetime.now_time());

			// Author label (UI convenience; server treats owner as canonical)
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

		// 3) Show/hide the follow-up block right away (not only on refresh)
		toggle_follow_up_fields(frm, !!frm.doc.requires_follow_up);

		// 4) Enable pre-submit assignment via the field (role-filtered)
		//    NOTE: we intentionally removed the old hard lock:
		//    // frm.set_df_property("follow_up_person", "read_only", 1);
		configure_follow_up_person_field(frm);
	}, 


	refresh(frm) {
		const status = (frm.doc.follow_up_status || "").toLowerCase();
		const requiresFU = !!frm.doc.requires_follow_up;

		// Show/hide the follow-up block consistently
		toggle_follow_up_fields(frm, requiresFU);

		// Assign / Reassign: only when follow-up is required AND doc is saved
		if (requiresFU && !frm.is_new()) {
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
								// Role-filtered picker (server filters users by role)
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

		// New Follow-Up: allowed unless already Closed (status is derived server-side)
		if (status !== "closed" && !frm.is_new()) {
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
			}, __("Actions"));
		}

		// Finalize: Close (admin OR owner). Calls server so timeline is logged.
		if (frm.doc.follow_up_status === "Completed" && !frm.is_new()) {
			const isOwner = (frappe.session.user === frm.doc.owner);
			if (frappe.user.has_role("Academic Admin") || isOwner) {
				frm.add_custom_button(__("Finalize: Close Log"), () => {
					frappe.call({
						method: "ifitwala_ed.students.doctype.student_log.student_log.finalize_close",
						args: { log_name: frm.doc.name },
						callback: () => frm.reload_doc()
					});
				}, __("Actions"));
			}
		}

		configure_follow_up_person_field(frm);	
	},

	student(frm) {
		// Auto-fill program + academic year from active enrollment
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
		// Optional helper to display the author's full name on the form
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
		// Update role based on Next Step, then refresh the role-filtered picker
		if (!frm.doc.next_step) {
			frm.set_value("follow_up_role", "Academic Staff");
			configure_follow_up_person_field(frm);
			return;
		}

		frappe.call({
			method: "ifitwala_ed.students.doctype.student_log.student_log.get_follow_up_role_from_next_step",
			args: { next_step: frm.doc.next_step },
			callback(r) {
				const role = r.message || "Academic Staff";
				frm.set_value("follow_up_role", role);

				// Re-apply pre-submit editability + role-filtered query for follow_up_person
				// (helper must be defined at file scope)
				configure_follow_up_person_field(frm);
			}
		});
	},


	requires_follow_up(frm) {
		const show = !!frm.doc.requires_follow_up;
		toggle_follow_up_fields(frm, show);

		// IMPORTANT:
		// - Do NOT set follow_up_status on client. Server derives + logs timeline.
		// - When switching OFF, clear fields locally for instant UX.
		if (!show) {
			frm.set_value("next_step", null);
			frm.set_value("follow_up_person", null);
			frm.set_value("follow_up_status", null);
		}
	},	
});

// Small helper to keep field toggling consistent
function toggle_follow_up_fields(frm, show) {
	frm.toggle_display(["next_step", "follow_up_role", "follow_up_person", "follow_up_status"], show);
}

function configure_follow_up_person_field(frm) {
	const requiresFU = !!frm.doc.requires_follow_up;

	// Editable only pre-submit when follow-up is required
	const editable_pre_submit = requiresFU && frm.is_new();
	frm.set_df_property("follow_up_person", "read_only", editable_pre_submit ? 0 : 1);

	// Role-filtered picker based on Next Step → associated_role (fallback: Academic Staff)
	const role = frm.doc.follow_up_role || "Academic Staff";
	frm.set_query("follow_up_person", () => ({
		query: "ifitwala_ed.api.get_users_with_role",
		filters: { role }
	}));
}


// Realtime toast for the author when a follow-up is created/submitted (server emits)
frappe.realtime.on("follow_up_ready_to_review", function (data) {
	frappe.show_alert({
		message: __("A follow-up for {0} is now ready for your review.", [data.student_name || data.log_name]),
		indicator: "green"
	});
});
