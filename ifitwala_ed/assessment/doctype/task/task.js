// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Task", {
	refresh(frm) {
		if (!frm.doc.__islocal && frm.doc.name) {
			add_duplicate_for_group_button(frm);
		}
	}
});

function add_duplicate_for_group_button(frm) {
	if (frm.custom_dup_btn) return;
	frm.custom_dup_btn = frm.add_custom_button(__("Duplicate for another group"), async () => {
		const dlg = new frappe.ui.Dialog({
			title: __("Duplicate Task"),
			fields: [
				{ fieldname: "new_student_group", fieldtype: "Link", label: __("Student Group"), options: "Student Group", reqd: 1 },
				{ fieldname: "section_dates", fieldtype: "Section Break", label: __("Dates (optional)") },
				{ fieldname: "available_from", fieldtype: "Datetime", label: __("Available From") },
				{ fieldname: "due_date", fieldtype: "Datetime", label: __("Due Date") },
				{ fieldname: "available_until", fieldtype: "Datetime", label: __("Available Until") },
				{ fieldname: "col1", fieldtype: "Column Break" },
				{ fieldname: "is_published", fieldtype: "Check", label: __("Publish immediately?") }
			],
			primary_action_label: __("Create"),
			primary_action: async (values) => {
				try {
					if (!values.new_student_group) {
						frappe.msgprint({ message: __("Please select a Student Group."), indicator: "orange" });
						return;
					}
					const res = await frappe.call({
						method: "ifitwala_ed.assessment.doctype.task.task.duplicate_for_group",
						args: {
							source_task: frm.doc.name,
							new_student_group: values.new_student_group,
							available_from: values.available_from || null,
							due_date: values.due_date || null,
							available_until: values.available_until || null,
							is_published: typeof values.is_published === "number" ? values.is_published : (values.is_published ? 1 : 0)
						},
						freeze: true,
						freeze_message: __("Creating task...")
					});
					dlg.hide();
					if (res && res.message && res.message.name) {
						frappe.show_alert({ message: __("Duplicated as {0}", [res.message.name]), indicator: "green" });
						frappe.set_route("Form", "Task", res.message.name);
					} else {
						frappe.msgprint({ message: __("Unexpected response"), indicator: "orange" });
					}
				} catch (e) {
					console.error(e);
					frappe.msgprint({ message: __("Failed to duplicate"), indicator: "red" });
				}
			}
		});
		dlg.show();
	});
}
