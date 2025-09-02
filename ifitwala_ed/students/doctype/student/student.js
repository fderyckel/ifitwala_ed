// Copyright (c) 2024, François de Ryckel 
// For license information, please see license.txt

// ifitwala_ed/students/doctype/student/student.js

frappe.ui.form.on('Student', {
	setup: function(frm) {
		frm.set_query('student', 'siblings', function(doc) {
			return {
				'filters': {'name': ['!=', doc.name]}
			};
		});
	},

	refresh: async function(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Student' };

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);

			// ✅ Check if linked Contact exists
			const r = await frappe.call({
				method: 'ifitwala_ed.students.doctype.student.student.get_contact_linked_to_student',
				args: { student_name: frm.doc.name }
			});

			// ✅ Add button only if a contact is found
			if (r.message) {
				frm.add_custom_button(__('Student Contact'), () => {
					frappe.set_route('Form', 'Contact', r.message);
				});
			}
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		// Only show Support button to target roles (server still gates data)
		if (frm.is_new()) return;

		const roles = (frappe.user_roles || []);
		const show =
			roles.includes("Counselor") ||
			roles.includes("Academic Admin") ||
			roles.includes("System Manager") ||
			roles.includes("Instructor");

		if (!show) return;

		const btn = frm.add_custom_button(__("Support"), () => open_support_modal(frm));
		btn.removeClass("btn-default").addClass("btn-info");
		btn.find("span").prepend(frappe.utils.icon("book-open", "sm"));
	}
});

async function open_support_modal(frm) {
	const student = frm.doc.name;
	if (!student) return;

	// Try to discover AYs that have SSG for this student (optional optimization).
	let ayOptions = [];
	try {
		const ssgs = await frappe.db.get_list("Student Support Guidance", {
			filters: { student },
			fields: ["name", "academic_year"],
			limit: 50
		});
		ayOptions = [...new Set((ssgs || []).map(r => r.academic_year))];
	} catch (e) {
		// ignore; we’ll fall back to defaults
	}

	const defaultAY =
		(frappe.defaults?.get_user_default?.("academic_year")) ||
		(frappe.boot?.sysdefaults?.academic_year) ||
		(ayOptions[0] || "");

	const d = new frappe.ui.Dialog({
		title: __("Student Support"),
		fields: [
			{
				fieldname: "academic_year",
				fieldtype: "Link",
				label: __("Academic Year"),
				options: "Academic Year",
				reqd: 1,
				default: defaultAY
			},
			{ fieldname: "snapshot", fieldtype: "HTML" },
			{ fieldname: "ack_sec", fieldtype: "Section Break" },
			{ fieldname: "ack_info", fieldtype: "HTML" },
			{ fieldname: "ack_cb", fieldtype: "Column Break" },
			{ fieldname: "ack", fieldtype: "Button", label: __("Acknowledge"), hidden: 1 }
		],
		primary_action_label: __("Close"),
		primary_action: () => d.hide()
	});

	// Wire AY change → refresh snapshot (debounced)
	const debouncedRefresh = frappe.utils.debounce(refresh_snapshot, 250);
	d.fields_dict.academic_year.$input.on("change", () => debouncedRefresh());

	// Wire Acknowledge (double-click safe)
	d.get_field("ack").$input.on("click", async () => {
		const btn = d.get_field("ack").$input;
		btn.prop("disabled", true);
		try {
			const ay = d.get_value("academic_year");
			await frappe.call({
				method: "ifitwala_ed.students.doctype.student_support_guidance.student_support_guidance.acknowledge_current_guidance",
				args: { student, academic_year: ay }
			});
			frappe.show_alert({ message: __("Acknowledged"), indicator: "green" });
			await refresh_snapshot();
		} catch (e) {
			frappe.msgprint({ message: __("Could not acknowledge."), indicator: "red" });
		} finally {
			btn.prop("disabled", false);
		}
	});

	async function refresh_snapshot() {
		const ay = d.get_value("academic_year");
		if (!ay) return;

		d.fields_dict.snapshot.$wrapper.html(`<div class="text-muted">${__("Loading…")}</div>`);
		d.set_df_property("ack", "hidden", 1);
		d.fields_dict.ack_info.$wrapper.empty();

		try {
			const [snap, ack] = await Promise.all([
				frappe.call({
					method: "ifitwala_ed.students.doctype.student_support_guidance.student_support_guidance.get_support_snapshot",
					args: { student, academic_year: ay }
				}),
				frappe.call({
					method: "ifitwala_ed.students.doctype.student_support_guidance.student_support_guidance.get_ack_status",
					args: { student, academic_year: ay }
				})
			]);

			const html =
				(snap.message && snap.message.snapshot_html) ||
				`<div class="text-muted">${__("No guidance yet.")}</div>`;
			d.fields_dict.snapshot.$wrapper.html(html);

			const s = (ack && ack.message) || {};
			if (!s.ack_required) {
				d.fields_dict.ack_info.$wrapper.html(
					`<div class="text-muted">${__("No acknowledgement required at this time.")}</div>`
				);
			} else if (s.has_open_todo) {
				d.fields_dict.ack_info.$wrapper.html(
					`<div class="text-warning">${__(
						"You have {0} item(s) to acknowledge (v{1}).",
						[(s.ack_required_count || 1), (s.ack_version || 0)]
					)}</div>`
				);
				d.set_df_property("ack", "hidden", 0);
			} else {
				d.fields_dict.ack_info.$wrapper.html(
					`<div class="text-success">${__("Acknowledged")}</div>`
				);
			}
		} catch (e) {
			// Permission denied or other error: keep it private.
			d.hide();
			frappe.msgprint({
				message: __("You are not permitted to view this support snapshot."),
				indicator: "red"
			});
		}
	}

	d.show();
	if (defaultAY) refresh_snapshot();
}
