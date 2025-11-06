// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/assessment/doctype/task/task.js

frappe.ui.form.on("Task", {
	setup(frm) {
		set_learning_unit_query(frm);
		set_lesson_query(frm);
	},

	refresh(frm) {
		console.debug("[Task.refresh] name:", frm.doc.name, "islocal:", frm.doc.__islocal, "student_group:", frm.doc.student_group);

		// Always add (or re-add) our buttons on refresh
		add_duplicate_for_group_button(frm);
		add_rubric_buttons(frm);

		// Live queries + controls
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		update_task_student_visibility(frm);
		add_or_toggle_load_students_buttons(frm);
		ensure_default_grade_scale(frm);

		// Auto-load on first meaningful state
		if (should_autoload_students(frm.doc) && !task_has_students(frm)) {
			try_load_students(frm);
		}

		// Client-only status preview for existing rows
		(frm.doc.task_student || []).forEach(r => apply_status_preview(frm, "Task Student", r.name));
	},

	after_save(frm) {
		// Keep UI responsive without a full refresh
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		add_or_toggle_load_students_buttons(frm);
		ensure_default_grade_scale(frm);

		if (should_autoload_students(frm.doc) && !task_has_students(frm)) {
			try_load_students(frm);
		}
	},

	student_group(frm) {
		// fetch_from fills course/school/program/ay → wait a tick then react
		setTimeout(() => {
			if (frm.doc.learning_unit) frm.set_value("learning_unit", null);
			if (frm.doc.lesson) frm.set_value("lesson", null);

			set_learning_unit_query(frm);
			set_lesson_query(frm);
			add_or_toggle_load_students_buttons(frm);
			ensure_default_grade_scale(frm);

			if (should_autoload_students(frm.doc) && !task_has_students(frm)) {
				try_load_students(frm);
			}
		}, 0);
	},

	course(frm) {
		if (frm.doc.learning_unit) frm.set_value("learning_unit", null);
		if (frm.doc.lesson) frm.set_value("lesson", null);
		set_learning_unit_query(frm);
		set_lesson_query(frm);
	},

	learning_unit(frm) {
		if (frm.doc.lesson) frm.set_value("lesson", null);
		set_lesson_query(frm);
	},

	// Toggle Task Student “complete” column visibility based on binary mode
	binary(frm) {
		update_task_student_visibility(frm);
	},

	// === Auto-load triggers on grading flags ================================
	is_graded(frm) {
		ensure_default_grade_scale(frm);
		if (should_autoload_students(frm.doc) && !task_has_students(frm)) ensure_saved_then(try_load_students, frm);
	},
	observations(frm) {
		if (should_autoload_students(frm.doc) && !task_has_students(frm)) ensure_saved_then(try_load_students, frm);
	},
	points(frm) {
		ensure_default_grade_scale(frm);
		if (should_autoload_students(frm.doc) && !task_has_students(frm)) ensure_saved_then(try_load_students, frm);
	},
	criteria(frm) {
		if (should_autoload_students(frm.doc) && !task_has_students(frm)) ensure_saved_then(try_load_students, frm);

		// Safety: clearing assessment_criteria when criteria unchecked
		if (!frm.doc.criteria) {
			const has_rows = (frm.doc.assessment_criteria || []).length > 0;
			if (has_rows) {
				frappe.confirm(
					__("Unchecking ‘Criteria’ will remove all linked Assessment Criteria rows. Continue?"),
					() => {
						frm.clear_table("assessment_criteria");
						frm.refresh_field("assessment_criteria");
					},
					() => frm.set_value("criteria", 1)
				);
			}
		}
	}
});

// --- Task Student childtable ------------------------------------------------
frappe.ui.form.on("Task Student", {
	total_mark(frm, cdt, cdn) {
		clamp_points_only(frm, cdt, cdn, "total_mark");
		apply_status_preview(frm, cdt, cdn);
	},
	mark_awarded(frm, cdt, cdn) {
		clamp_points_only(frm, cdt, cdn, "mark_awarded");
		apply_status_preview(frm, cdt, cdn);
	},
	feedback(frm, cdt, cdn) {
		apply_status_preview(frm, cdt, cdn);
	},
	complete(frm, cdt, cdn) { // binary mode
		apply_status_preview(frm, cdt, cdn);
	},
	visible_to_student: visibility_toggled,
	visible_to_guardian: visibility_toggled
});

// --- Buttons ---------------------------------------------------------------

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

function add_or_toggle_load_students_buttons(frm) {
	const can_show = !!frm.doc.name;
	const has_group = !!frm.doc.student_group;

	if (!frm.__load_students_toolbar_btn_added) {
		frm.__load_students_toolbar_btn_added = true;
		frm.add_custom_button(__("Load Students"), () => try_load_students(frm), __("Students"));
		frm.page.set_inner_btn_group_as_primary(__("Students"));
	}
	frm.toggle_custom_button(__("Load Students"), can_show && has_group, __("Students"));

	const grid = frm.fields_dict?.task_student?.grid;
	if (grid && !grid.__load_students_grid_btn_added) {
		grid.__load_students_grid_btn_added = true;
		grid.add_custom_button(__("Load Students"), () => try_load_students(frm));
	}
}

// --- Dialogs (Rubric) ------------------------------------------------------

function add_rubric_buttons(frm) {
	const grid_field = frm.fields_dict["task_student"];
	if (!grid_field || !grid_field.grid) return;

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
				// Client-side clamp: 0 ≤ level_points ≤ criterion cap
				const caps = {};
				(frm.doc.assessment_criteria || []).forEach(r => {
					if (r.assessment_criteria) caps[r.assessment_criteria] = Number(r.criteria_max_points || 0);
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
				await frappe.call({
					method: "ifitwala_ed.assessment.doctype.task.task.recompute_student_totals",
					args: { task: frm.doc.name, student }
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
		if (r.message && Array.isArray(r.message.rows)) dlg.set_value("criteria_rows", r.message.rows);
	});
}

// --- Queries & Guards ------------------------------------------------------

function set_learning_unit_query(frm) {
	frm.set_query("learning_unit", () => {
		const course = (frm.doc.course || "").trim();
		if (!course) return { filters: { name: ["=", "__none__"] } };
		return { filters: { course, unit_status: "Active" } }; // add is_published: 1 if desired
	});
}

function set_lesson_query(frm) {
	frm.set_query("lesson", () => {
		const lu = (frm.doc.learning_unit || "").trim();
		if (!lu) return { filters: { name: ["=", "__none__"] } };
		return { filters: { learning_unit: lu } };
	});
}

function should_autoload_students(doc) {
	return !!doc.student_group && (
		!!doc.is_graded ||
		!!doc.observations ||
		!!doc.binary ||
		!!doc.points ||
		!!doc.criteria
	);
}

function task_has_students(frm) {
	return (frm.doc.task_student || []).length > 0;
}

async function ensure_saved_then(fn, frm) {
	if (frm.is_dirty() || frm.is_new()) await frm.save();
	await fn(frm);
}

async function try_load_students(frm) {
	if (!frm.doc.student_group) {
		frappe.msgprint({ message: __("Please select a Student Group first."), indicator: "orange" });
		return;
	}
	if (!frm.doc.name) {
		await ensure_saved_then(try_load_students, frm);
		return;
	}
	if (frm.__students_autoloaded_once) return;

	try {
		const res = await frappe.call({
			method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_students",
			args: { task: frm.doc.name },
			freeze: true,
			freeze_message: __("Loading students...")
		});
		frm.__students_autoloaded_once = true;
		if (res.message) {
			frappe.show_alert({
				message: `${res.message.inserted} ${__("students added")} (${res.message.total} ${__("eligible")})`,
				indicator: "green"
			});
			await frm.reload_doc();
		}
	} catch (e) {
		console.error(e);
		frappe.msgprint({ message: __("Failed to load students"), indicator: "red" });
	}
}

// Cache to avoid repeated DB hits per course
const __gradeScaleCache = Object.create(null);

async function ensure_default_grade_scale(frm) {
	// Only when grading is relevant
	if (!(frm.doc.is_graded || frm.doc.points)) return;
	// Need a course selected
	if (!frm.doc.course) return;
	// Don’t overwrite if already set
	if (frm.doc.grade_scale) return;

	const course = frm.doc.course;
	// Memoized lookup
	if (!(__gradeScaleCache.hasOwnProperty(course))) {
		const r = await frappe.db.get_value("Course", course, "default_grade_scale");
		__gradeScaleCache[course] = r?.message?.default_grade_scale || null;
	}
	const gs = __gradeScaleCache[course];
	if (gs) {
		await frm.set_value("grade_scale", gs);
		// Optional toast:
		frappe.show_alert({ message: __("Loaded default grade scale from Course"), indicator: "blue" });
	}
}


// --- Points & Visibility & Status Preview ----------------------------------

function has_any_criteria(frm) {
	return Array.isArray(frm.doc.assessment_criteria) &&
		frm.doc.assessment_criteria.some(r => r.assessment_criteria);
}

function clamp_points_only(frm, cdt, cdn, fieldname) {
	// Only enforce in "points-only" mode (no criteria on this Task)
	if (has_any_criteria(frm)) return;

	const cap = Number(frm.doc.max_points || 0);
	const d = frappe.get_doc(cdt, cdn);
	let v = Number(d[fieldname] || 0);

	if (Number.isNaN(v)) v = 0;
	let clamped = (cap > 0) ? Math.min(Math.max(0, v), cap) : Math.max(0, v);

	if (clamped !== v) {
		frappe.model.set_value(cdt, cdn, fieldname, clamped);
		frappe.show_alert({
			message: __("{0} adjusted to stay within 0 and Task Max Points.", [frappe.meta.get_label(cdt, fieldname, cdn)]),
			indicator: "orange"
		});
	}
}

function update_task_student_visibility(frm) {
	const grid = frm.fields_dict?.task_student?.grid;
	if (!grid) return;
	const showComplete = !!frm.doc.binary;
	grid.set_column_disp("complete", showComplete);
	grid.refresh();
}

// Client-only status preview; server remains source of truth
function task_has_criteria(frm) {
	return Array.isArray(frm.doc.assessment_criteria) &&
		frm.doc.assessment_criteria.some(r => r.assessment_criteria);
}

function compute_status_preview(frm, row) {
	if (row.visible_to_student || row.visible_to_guardian) return "Returned";
	if (frm.doc.binary && row.complete) return "Graded";
	if (row.mark_awarded !== null && row.mark_awarded !== undefined && row.mark_awarded !== "") return "Graded";
	if ((row.feedback || "").trim()) return "Graded";

	if (!task_has_criteria(frm)) {
		const hasTotal = (row.total_mark !== null && row.total_mark !== undefined && row.total_mark !== "");
		const hasFinal = (row.mark_awarded !== null && row.mark_awarded !== undefined && row.mark_awarded !== "");
		if (hasTotal && !hasFinal) return "In Progress";
	}
	return "Assigned";
}

function apply_status_preview(frm, cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	const newStatus = compute_status_preview(frm, row);
	if (row.status !== newStatus) {
		frappe.model.set_value(cdt, cdn, "status", newStatus);
	}
}

function visibility_toggled(frm, cdt, cdn) {
	apply_status_preview(frm, cdt, cdn);
}
