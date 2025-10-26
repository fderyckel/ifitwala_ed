// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

//ifitwala_ed/assessment/doctype/task/task.js

frappe.ui.form.on("Task", {
	refresh(frm) {
		if (!frm.doc.__islocal && frm.doc.name) {
			add_duplicate_for_group_button(frm);
			add_load_students_button(frm);
			add_rubric_buttons(frm);
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

function add_load_students_button(frm) {
	if (frm.custom_load_btn) return;
	frm.custom_load_btn = frm.add_custom_button(__("Load Students"), async () => {
		frappe.call({
			method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_students",
			args: { task: frm.doc.name },
			freeze: true,
			freeze_message: __("Loading students...")
		}).then(res => {
			if (res.message) {
				frappe.show_alert({ message: `${res.message.inserted} students added (of ${res.message.total})`, indicator: 'green' });
				frm.reload_doc();
			}
		});
	});
}

function add_rubric_buttons(frm) {
	// Add a button under the Gradebook child table for rubric dialog and bulk apply suggestion
	const grid_field = frm.fields_dict["task_student"];
	if (!grid_field) return;

	grid_field.grid.add_custom_button(__("Apply Rubric Suggestions → Mark Awarded"), async () => {
		const selected = grid_field.grid.get_selected_children();
		if (!selected || !selected.length) {
			frappe.msgprint({ message: __("Please select at least one student row."), indicator: "orange" });
			return;
		}
		let student_list = selected.map(r => r.student);
		frappe.call({
			method: "ifitwala_ed.assessment.doctype.task.task.apply_rubric_to_awarded",
			args: {
				task: frm.doc.name,
				students: student_list
			},
			freeze: true,
			freeze_message: __("Applying rubric suggestions...")
		}).then(r => {
			frappe.show_alert({ message: __("Mark Awarded updated for {0} students", [student_list.length]), indicator: 'blue' });
			frm.reload_doc();
		});
	});

	// Row-level rubric button via child table row custom field or link
	frm.fields_dict["task_student"].grid.wrapper.on('click', '.btn-rubric', function(e) {
		const row = frappe.ui.get_grid_row(this);
		const data = row.doc;
		open_rubric_dialog(frm, data.student, data.student_name);
	});
}

function open_rubric_dialog(frm, student, student_name) {
	const dlg = new frappe.ui.Dialog({
		title: __("Edit Rubric for {0}", [student_name]),
		fields: [
			{ fieldname: "criteria_rows", fieldtype: "Table", options: "Task Criterion Score", label: __("Rubric Rows"), reqd: 1 }
		],
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			try {
				const res = await frappe.call({
					method: "ifitwala_ed.assessment.gradebook_utils.upsert_task_criterion_scores",
					args: {
						task: frm.doc.name,
						student: student,
						rows: values.criteria_rows
					},
					freeze: true,
					freeze_message: __("Saving rubric rows...")
				});
				dlg.hide();
				if (res && res.message && res.message.suggestion !== undefined) {
					frappe.show_alert({ message: __("Suggestion {0}", [res.message.suggestion]), indicator: 'blue' });
					frm.reload_doc();
				}
			} catch (e) {
				console.error(e);
				frappe.msgprint({ message: __("Failed to save rubric rows"), indicator: "red" });
			}
		}
	});
	dlg.show();

	// Prefill the table with existing rows (fetch via server if you like)
	frappe.call({
		method: "ifitwala_ed.assessment.doctype.task.task.get_criterion_scores_for_student",
		args: { task: frm.doc.name, student: student },
	}).then(r => {
		if (r.message && Array.isArray(r.message.rows)) {
			dlg.set_value("criteria_rows", r.message.rows);
		}
	});
}
