// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/assessment/doctype/task/task.js

frappe.ui.form.on("Task", {
	setup(frm) {
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		make_is_graded_readonly(frm);
	},

	refresh(frm) {
		derive_is_graded(frm);
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		update_task_student_visibility(frm);
		ensure_points_field_rules(frm);       // show/require max_points only when points==1
		ensure_default_grade_scale(frm);      // only when points==1 & empty
		auto_sync_students_if_needed(frm);    // add-only; no removals
		auto_seed_rubrics_if_needed(frm);     // if criteria==1 and students exist

		// Client-only status preview
		(frm.doc.task_student || []).forEach(r => apply_status_preview(frm, "Task Student", r.name));
	},

	after_save(frm) {
		derive_is_graded(frm);
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		ensure_points_field_rules(frm);
		ensure_default_grade_scale(frm);
		auto_sync_students_if_needed(frm);
		auto_seed_rubrics_if_needed(frm);
	},

	student_group(frm) {
		// fetch_from will populate course/school/program/ay; clear dependent fields safely
		setTimeout(() => {
			if (frm.doc.learning_unit) frm.set_value("learning_unit", null);
			if (frm.doc.lesson) frm.set_value("lesson", null);

			set_learning_unit_query(frm);
			set_lesson_query(frm);

			derive_is_graded(frm);
			ensure_points_field_rules(frm);
			ensure_default_grade_scale(frm);
			auto_sync_students_if_needed(frm);
			auto_seed_rubrics_if_needed(frm);
		}, 0);
	},

	course(frm) {
		if (frm.doc.learning_unit) frm.set_value("learning_unit", null);
		if (frm.doc.lesson) frm.set_value("lesson", null);
		set_learning_unit_query(frm);
		set_lesson_query(frm);

		// Course change might unlock default grade scale (points flow)
		ensure_default_grade_scale(frm);
	},

	learning_unit(frm) {
		if (frm.doc.lesson) frm.set_value("lesson", null);
		set_lesson_query(frm);
	},

	// --- grading toggles ----------------------------------------------------
	binary(frm) {
		derive_is_graded(frm);
		update_task_student_visibility(frm);
		auto_sync_students_if_needed(frm);
	},
	observations(frm) {
		derive_is_graded(frm);
		auto_sync_students_if_needed(frm);
	},
	points(frm) {
		derive_is_graded(frm);
		ensure_points_field_rules(frm);
		ensure_default_grade_scale(frm);
		auto_sync_students_if_needed(frm);
	},
	criteria(frm) {
		derive_is_graded(frm);
		auto_sync_students_if_needed(frm);
		auto_seed_rubrics_if_needed(frm);

		// Safety: clearing criteria table if unchecked
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

// ----------------- Child table: Task Student -------------------------------
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
	complete(frm, cdt, cdn) {
		apply_status_preview(frm, cdt, cdn);
	},
	visible_to_student: visibility_toggled,
	visible_to_guardian: visibility_toggled
});

// ----------------- Queries -------------------------------------------------
function set_learning_unit_query(frm) {
	frm.set_query("learning_unit", () => {
		const course = (frm.doc.course || "").trim();
		if (!course) return { filters: { name: ["=", "__none__"] } };
		return { filters: { course, unit_status: "Active" } };
	});
}
function set_lesson_query(frm) {
	frm.set_query("lesson", () => {
		const lu = (frm.doc.learning_unit || "").trim();
		if (!lu) return { filters: { name: ["=", "__none__"] } };
		return { filters: { learning_unit: lu } };
	});
}

// ----------------- Derived + UI rules --------------------------------------
function make_is_graded_readonly(frm) {
	frm.set_df_property("is_graded", "read_only", 1);
}
function derive_is_graded(frm) {
	const val = !!(frm.doc.points || frm.doc.criteria || frm.doc.binary || frm.doc.observations);
	if (frm.doc.is_graded !== (val ? 1 : 0)) {
		frm.set_value("is_graded", val ? 1 : 0);
	}
}
function ensure_points_field_rules(frm) {
	// Show + require max_points only when points==1
	const on = !!frm.doc.points;
	frm.set_df_property("max_points", "hidden", !on);
	frm.set_df_property("max_points", "reqd", on);
	if (!on && frm.doc.max_points) frm.set_value("max_points", null);
}

// ----------------- Auto load (add-only) & rubric seeding -------------------
function should_sync_students(doc) {
	return !!doc.student_group && !!(doc.points || doc.criteria || doc.binary || doc.observations);
}
async function ensure_saved_then(fn, frm) {
	if (frm.is_dirty() || frm.is_new()) await frm.save();
	await fn(frm);
}
async function auto_sync_students_if_needed(frm) {
	if (!should_sync_students(frm.doc)) return;
	if (!frm.doc.name) return ensure_saved_then(auto_sync_students_if_needed, frm);

	try {
		const res = await frappe.call({
			method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_students",
			args: { task: frm.doc.name },
			freeze: false
		});
		// Idempotent: adds only missing students; never removes.
		if (res?.message?.inserted > 0) {
			frappe.show_alert({ message: __("{0} students added from group.", [res.message.inserted]), indicator: "green" });
			await frm.reload_doc();
		}
	} catch (e) {
		console.error(e);
	}
}
async function auto_seed_rubrics_if_needed(frm) {
	// Only matters when criteria==1 and students exist
	if (!frm.doc.criteria) return;
	if (!frm.doc.name) return;
	if (!(frm.doc.task_student || []).length) return;

	try {
		// Reuse your server-side rubric prefill via saving (already runs on server save path in task.py),
		// or explicitly call recompute per student after edits in rubric dialog.
		// Here we just keep client lean; server handles prefill on save.
	} catch (e) {
		console.error(e);
	}
}

// ----------------- Grade scale (points-only trigger) -----------------------
const __gradeScaleCache = Object.create(null); // safe dict
async function ensure_default_grade_scale(frm) {
	// Only when POINTS is on
	if (!frm.doc.points) return;
	if (!frm.doc.course) return;
	if (frm.doc.grade_scale) return;

	const course = frm.doc.course;
	// Safe hasOwnProperty
	if (!Object.prototype.hasOwnProperty.call(__gradeScaleCache, course)) {
		const r = await frappe.db.get_value("Course", course, "default_grade_scale");
		__gradeScaleCache[course] = r?.message?.default_grade_scale || null;
	}
	const gs = __gradeScaleCache[course];
	if (gs) {
		await frm.set_value("grade_scale", gs);
		frappe.show_alert({ message: __("Loaded default grade scale from Course"), indicator: "blue" });
	}
}

// ----------------- Points clamp & visibility & status preview --------------
function has_any_criteria(frm) {
	return Array.isArray(frm.doc.assessment_criteria) &&
		frm.doc.assessment_criteria.some(r => r.assessment_criteria);
}
function clamp_points_only(frm, cdt, cdn, fieldname) {
	// Only in points-only (no criteria)
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
	grid.set_column_disp("complete", !!frm.doc.binary);
	grid.refresh();
}
function task_has_criteria(frm) {
	return has_any_criteria(frm);
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
