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

	refresh(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Student' };

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
			frappe.call({
				method: 'ifitwala_ed.students.doctype.student.student.get_contact_linked_to_student',
				args: { student_name: frm.doc.name }
			}).then(r => {
				if (r && r.message) {
					frm.add_custom_button(__('Student Contact'), () => {
						frappe.set_route('Form', 'Contact', r.message);
					});
				}
			});
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		// Gate by roles (server still re-checks permissions)
		if (frm.is_new()) return;

		const canSeeSupport =
			frappe.user.has_role("Counselor") ||
			frappe.user.has_role("Academic Admin") ||
			frappe.user.has_role("System Manager") ||
			frappe.user.has_role("Instructor");

		if (!canSeeSupport) return;

		const btn = frm.add_custom_button(__("Support"), () => open_support_modal(frm), __("Actions"));
		btn.removeClass("btn-default").addClass("btn-info");
		btn.find("span").prepend(frappe.utils.icon("book-open", "sm"));
	}
});


function open_support_modal(frm) {
	const student = frm.doc.name;
	if (!student) return;

	// Resolve a default AY quickly (no prefetch; dialog shows immediately)
	const defaultAY =
		(frappe.defaults && frappe.defaults.get_user_default && frappe.defaults.get_user_default("academic_year")) ||
		(frappe.boot && frappe.boot.sysdefaults && frappe.boot.sysdefaults.academic_year) ||
		"";

	const d = new frappe.ui.Dialog({
		title: __("Student Support"),
		fields: [
			{ fieldname: "academic_year", fieldtype: "Link", label: __("Academic Year"), options: "Academic Year", reqd: 1, default: defaultAY },
			{ fieldname: "snapshot", fieldtype: "HTML" },
			{ fieldname: "ack_sec", fieldtype: "Section Break" },
			{ fieldname: "ack_info", fieldtype: "HTML" },
			{ fieldname: "ack_cb", fieldtype: "Column Break" },
			{ fieldname: "ack", fieldtype: "Button", label: __("Acknowledge"), hidden: 1 }
		],
		primary_action_label: __("Close"),
		primary_action: () => d.hide()
	});

	// Debounced refresh when AY changes
	const refreshDebounced = frappe.utils.debounce(() => refresh_snapshot(d, student), 250);
	d.fields_dict.academic_year.$input.on("change", refreshDebounced);

	// Wire Acknowledge
	d.get_field("ack").$input.on("click", async () => {
		const btn = d.get_field("ack").$input;
		btn.prop("disabled", true);
		try {
			const ay = d.get_value("academic_year");
			await frappe.call({
				method: "ifitwala_ed.students.doctype.student_support_guidance.student_support_guidance.acknowledge_current_guidance",
				args: { student, academic_year: ay },
				freeze: true,
				freeze_message: __("Submitting acknowledgement…")
			});
			frappe.show_alert({ message: __("Acknowledged"), indicator: "green" });
			await refresh_snapshot(d, student);
		} catch (e) {
			console.error(e);
			frappe.msgprint({ message: __("Could not acknowledge."), indicator: "red" });
		} finally {
			btn.prop("disabled", false);
		}
	});

	d.show();
	// First load
	refresh_snapshot(d, student).catch(e => {
		console.error(e);
		d.hide();
		frappe.msgprint({ message: __("Unable to open support snapshot."), indicator: "red" });
	});
}

async function refresh_snapshot(d, student) {
	const ay = d.get_value("academic_year");
	if (!ay) {
		d.fields_dict.snapshot.$wrapper.html(`<div class="text-muted">${__("Choose an Academic Year.")}</div>`);
		d.set_df_property("ack", "hidden", 1);
		d.fields_dict.ack_info.$wrapper.empty();
		return;
	}

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
			(snap && snap.message && snap.message.snapshot_html) ||
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
			d.fields_dict.ack_info.$wrapper.html(`<div class="text-success">${__("Acknowledged")}</div>`);
		}
	} catch (e) {
		console.error(e);
		// Permission denied or other server error
		d.hide();
		frappe.msgprint({
			message: __("You are not permitted to view this support snapshot."),
			indicator: "red"
		});
	}
}