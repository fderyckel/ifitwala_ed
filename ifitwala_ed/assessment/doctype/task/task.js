// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/assessment/doctype/task/task.js

frappe.ui.form.on("Task", {
	setup(frm) {
		set_learning_unit_query(frm);
	},

	refresh(frm) {
		console.debug("[Task.refresh] name:", frm.doc.name, "islocal:", frm.doc.__islocal, "student_group:", frm.doc.student_group);

		// Always add (or re-add) our buttons on refresh
		add_duplicate_for_group_button(frm);
		add_load_students_buttons(frm);     // <— consolidated
		add_rubric_buttons(frm);
		set_learning_unit_query(frm);
	},


	student_group(frm) {
		// student_group → auto-fetch course via fetch_from
		// Defer a tick to ensure fetch_from landed before we clear children
		setTimeout(() => on_course_changed(frm), 0);
	},

	course(frm) {
		on_course_changed(frm);
	}


});

// Child table client rules for Task Student (points-only clamp)
frappe.ui.form.on("Task Student", {
	total_mark: function(frm, cdt, cdn) {
		clamp_points_only(frm, cdt, cdn, "total_mark");
	},
	mark_awarded: function(frm, cdt, cdn) {
		clamp_points_only(frm, cdt, cdn, "mark_awarded");
	}
});


function add_duplicate_for_group_button(frm) {
	if (frm.__dup_btn_added) return;
	frm.__dup_btn_added = true;

	frm.add_custom_button(__("Duplicate for another group"), async () => {
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
							is_published: values.is_published ? 1 : 0
						},
						freeze: true,
						freeze_message: __("Creating task...")
					});
					dlg.hide();
					if (res?.message?.name) {
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
	}, __("Actions"));
}

function set_learning_unit_query(frm) {
	frm.set_query("learning_unit", () => {
		const course = (frm.doc.course || "").trim();
		// If no course yet, return a false filter that yields nothing
		if (!course) {
			return {
				filters: { name: ["=", "__none__"] }
			};
		}
		// Minimal, index-friendly filters
		return {
			filters: {
				course: course,
				unit_status: "Active" // optional but sensible; remove if you want all
				// is_published: 1   // uncomment if you only want published units
			}
		};
	});
}

// Clear dependent fields when upstream changes (to avoid stale selections)
function on_course_changed(frm) {
	if (frm.doc.learning_unit) frm.set_value("learning_unit", null);
	if (frm.doc.lesson) frm.set_value("lesson", null);
	set_learning_unit_query(frm);
}

/**
 * Add "Load Students" in two places:
 *  1) Form toolbar under group "Students"
 *  2) Inside the Task Student grid’s dropdown menu
 * Button is enabled only when doc is saved and student_group is set.
 */
function add_load_students_buttons(frm) {
	const can_show = !frm.doc.__islocal && !!frm.doc.name;
	const has_group = !!frm.doc.student_group;

	// 1) Toolbar button (grouped under "Students")
	if (!frm.__load_students_toolbar_btn_added) {
		frm.__load_students_toolbar_btn_added = true;
		frm.add_custom_button(__("Load Students"), () => try_load_students(frm), __("Students"));
	}
	// Show/hide based on conditions
	frm.page.set_inner_btn_group_as_primary(__("Students"));
	frm.toggle_custom_button(__("Load Students"), can_show, __("Students"));

	// Provide quick hint if blocked
	if (can_show && !has_group) {
		frm.dashboard.set_headline_alert(__("Select a Student Group to enable <b>Load Students</b>."), "orange");
	}

	// 2) Grid menu button on Task Student child table
	const grid = frm.fields_dict?.task_student?.grid;
	if (grid && !grid.__load_students_grid_btn_added) {
		grid.__load_students_grid_btn_added = true;
		grid.add_custom_button(__("Load Students"), () => try_load_students(frm));
	}
}

async function try_load_students(frm) {
	if (!frm.doc.student_group) {
		frappe.msgprint({ message: __("Please select a Student Group first."), indicator: "orange" });
		return;
	}
	if (frm.doc.__islocal) {
		frappe.msgprint({ message: __("Please save the Task before loading students."), indicator: "orange" });
		return;
	}

	try {
		const res = await frappe.call({
			method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_students",
			args: { task: frm.doc.name },
			freeze: true,
			freeze_message: __("Loading students...")
		});
		if (res.message) {
			frappe.show_alert({ message: `${res.message.inserted} ${__("students added")} (${res.message.total} ${__("eligible")})`, indicator: 'green' });
			frm.reload_doc();
		}
	} catch (e) {
		console.error(e);
		frappe.msgprint({ message: __("Failed to load students"), indicator: "red" });
	}
}

function add_rubric_buttons(frm) {
	const grid_field = frm.fields_dict["task_student"];
	if (!grid_field || !grid_field.grid) return;

	// Add “bulk apply” to the grid menu
	if (!grid_field.grid.__rubric_bulk_btn_added) {
		grid_field.grid.__rubric_bulk_btn_added = true;
		grid_field.grid.add_custom_button(__("Apply Rubric Suggestions → Mark Awarded"), async () => {
			const selected = grid_field.grid.get_selected_children();
			if (!selected?.length) {
				frappe.msgprint({ message: __("Please select at least one student row."), indicator: "orange" });
				return;
			}
			const student_list = selected.map(r => r.student);
			try {
				const r = await frappe.call({
					method: "ifitwala_ed.assessment.doctype.task.task.apply_rubric_to_awarded",
					args: { task: frm.doc.name, students: student_list },
					freeze: true,
					freeze_message: __("Applying rubric suggestions...")
				});
				frappe.show_alert({ message: __("Mark Awarded updated for {0} students", [student_list.length]), indicator: 'blue' });
				frm.reload_doc();
			} catch (e) {
				console.error(e);
				frappe.msgprint({ message: __("Failed to apply rubric suggestions"), indicator: "red" });
			}
		});
	}

	// Optional: per-row action hook (kept from your original)
	grid_field.grid.wrapper.on('click', '.btn-rubric', function () {
		const row = frappe.ui.get_grid_row(this);
		const data = row.doc;
		open_rubric_dialog(frm, data.student, data.student_name);
	});
}

function open_rubric_dialog(frm, student, student_name) {
	const dlg = new frappe.ui.Dialog({
		title: __("Edit Rubric for {0}", [student_name]),
		fields: [{ fieldname: "criteria_rows", fieldtype: "Table", options: "Task Criterion Score", label: __("Rubric Rows"), reqd: 1 }],
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			try {
				// Clamp client-side: 0 ≤ level_points ≤ criterion cap
				const caps = {};
				(frm.doc.assessment_criteria || []).forEach(r => {
					if (r.assessment_criteria) {
						caps[r.assessment_criteria] = Number(r.criteria_max_points || 0);
					}
				});
				let clampedCount = 0;
				(values.criteria_rows || []).forEach(row => {
					const cap = Number(caps[row.assessment_criteria] || 0);
					let v = Number(row.level_points || 0);
					if (Number.isNaN(v)) v = 0;
					const clamped = Math.max(0, cap > 0 ? Math.min(v, cap) : Math.max(0, v));
					if (clamped !== v) clampedCount++;
					row.level_points = clamped;
				});
				if (clampedCount > 0) {
					frappe.show_alert({
						message: __("{0} rubric entries adjusted to stay within 0 and criterion max.", [clampedCount]),
						indicator: "orange"
					});
				}

				const res = await frappe.call({
					method: "ifitwala_ed.assessment.gradebook_utils.upsert_task_criterion_scores",
					args: { task: frm.doc.name, student, rows: values.criteria_rows },
					freeze: true,
					freeze_message: __("Saving rubric rows...")
				});
				// Recompute Task Student totals for this learner
				await frappe.call({
					method: "ifitwala_ed.assessment.doctype.task.task.recompute_student_totals",
					args: { task: frm.doc.name, student },
					freeze: false
				});
				dlg.hide();
				if (res?.message?.suggestion !== undefined) {
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

	frappe.call({
		method: "ifitwala_ed.assessment.doctype.task.task.get_criterion_scores_for_student",
		args: { task: frm.doc.name, student }
	}).then(r => {
		if (r.message && Array.isArray(r.message.rows)) {
			dlg.set_value("criteria_rows", r.message.rows);
		}
	});
}


// Helpers for childtable task student points.
function has_any_criteria(frm) {
	return Array.isArray(frm.doc.assessment_criteria) &&
		frm.doc.assessment_criteria.some(r => r.assessment_criteria);
}

function clamp_points_only(frm, cdt, cdn, fieldname) {
	// Only enforce in the "points-only" case: no criteria on this Task
	if (has_any_criteria(frm)) return;

	const cap = Number(frm.doc.max_points || 0);
	const d = frappe.get_doc(cdt, cdn);
	let v = Number(d[fieldname] || 0);

	if (Number.isNaN(v)) v = 0;
	let clamped = v;
	if (cap > 0) clamped = Math.min(Math.max(0, v), cap);
	else clamped = Math.max(0, v); // if cap is 0/blank, just prevent negatives

	if (clamped !== v) {
		frappe.model.set_value(cdt, cdn, fieldname, clamped);
		frappe.show_alert({
			message: __("{0} adjusted to stay within 0 and Task Max Points.", [frappe.meta.get_label(cdt, fieldname, cdn)]),
			indicator: "orange"
		});
	}
}
