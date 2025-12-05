// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/assessment/doctype/task/task.js

frappe.ui.form.on("Task", {
	setup(frm) {
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		make_is_graded_readonly(frm);
		set_assessment_criteria_query(frm);
	},

	refresh(frm) {
		derive_is_graded(frm);
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		update_task_student_visibility(frm);
		ensure_points_field_rules(frm);       // show/require max_points only when points==1
		// NOTE: no ensure_default_grade_scale() here anymore
		auto_sync_students_if_needed(frm);    // add-only; no removals
		auto_seed_rubrics_if_needed(frm);     // if criteria==1 and students exist
		set_assessment_criteria_query(frm);

		// Client-only status preview
		(frm.doc.task_student || []).forEach(r => apply_status_preview(frm, "Task Student", r.name));
	},

	after_save(frm) {
		// Keep this light; no network calls here
		derive_is_graded(frm);
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		ensure_points_field_rules(frm);
		// no ensure_default_grade_scale(), no auto_sync, no auto_seed
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
			ensure_default_grade_scale(frm);   // allowed here
			auto_sync_students_if_needed(frm);
			auto_seed_rubrics_if_needed(frm);
		}, 0);
	},

	course(frm) {
		if (frm.doc.learning_unit) frm.set_value("learning_unit", null);
		if (frm.doc.lesson) frm.set_value("lesson", null);
		set_learning_unit_query(frm);
		set_lesson_query(frm);

		// Load + apply criteria filter for new course
		load_course_criteria(frm).then(() => {
			set_assessment_criteria_query(frm);
		});

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
		ensure_default_grade_scale(frm);      // keep here
		auto_sync_students_if_needed(frm);
	},
	criteria(frm) {
		// Always keep is_graded in sync
		derive_is_graded(frm);

		// Turning Criteria OFF
		if (!frm.doc.criteria) {
			const has_rows =
				(frm.doc.assessment_criteria || []).length > 0 ||
				(frm.doc.task_criterion_score || []).length > 0;

			// If any grading has started, block and revert immediately
			if (has_grading_activity(frm)) {
				frappe.msgprint({
					title: __("Cannot Disable Criteria"),
					message: __(
						"Grading has already started for this Task. " +
						"You cannot turn off Criteria without losing data. " +
						"Please duplicate the Task if you need a different grading mode."
					),
					indicator: "red",
				});
				frm.set_value("criteria", 1);
				return;
			}

			// No grading yet: it's safe to clear, but ask first
			if (has_rows) {
				frappe.confirm(
					__(
						"Unchecking ‘Criteria’ will remove all linked Assessment Criteria and rubric scores. Continue?"
					),
					() => {
						frm.clear_table("assessment_criteria");
						frm.clear_table("task_criterion_score");
						frm.refresh_field("assessment_criteria");
						frm.refresh_field("task_criterion_score");
					},
					() => {
						// User cancelled → restore criteria checkbox
						frm.set_value("criteria", 1);
					}
				);
			}

			// When turning OFF, we do NOT auto-sync students or seed rubrics
			return;
		}

		// Turning Criteria ON
		// Normal behaviour: keep auto-sync + future rubric seeding
		auto_sync_students_if_needed(frm);
		auto_seed_rubrics_if_needed(frm);
	},
});

// ----------------- Child table: Task Student -------------------------------
frappe.ui.form.on("Task Student", {
	student(frm, cdt, cdn) {
		prevent_duplicate_task_student(frm, cdt, cdn);
	},
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
function has_grading_activity(frm) {
	// Check Task Student rows
	for (const row of (frm.doc.task_student || [])) {
		const has_mark_awarded = row.mark_awarded !== undefined && row.mark_awarded !== null && row.mark_awarded !== "";
		const has_total_mark  = row.total_mark  !== undefined && row.total_mark  !== null && row.total_mark  !== "";
		const has_feedback    = (row.feedback || "").trim().length > 0;
		const has_flags       = !!(row.complete || row.visible_to_student || row.visible_to_guardian);
		const status          = row.status || "";

		if (has_mark_awarded || has_total_mark || has_feedback || has_flags || (status && status !== "Assigned")) {
			return true;
		}
	}

	// Check rubric rows
	for (const r of (frm.doc.task_criterion_score || [])) {
		const hasLevel = !!(r.level && String(r.level).trim());
		const pts = Number(r.level_points || 0);
		const hasRubricFeedback = (r.feedback || "").trim().length > 0;

		if (hasLevel || pts !== 0 || hasRubricFeedback) {
			return true;
		}
	}

	return false;
}


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

	// Grade Scale is only relevant in points mode (server requires it)
	frm.set_df_property("grade_scale", "hidden", !on);
	frm.set_df_property("grade_scale", "reqd", on);
	if (!on && frm.doc.grade_scale) frm.set_value("grade_scale", null);
}

const __courseCriteriaCache = Object.create(null);

async function load_course_criteria(frm) {
	const course = (frm.doc.course || "").trim();
	if (!course) return;

	// Don’t refetch if already cached
	if (Object.prototype.hasOwnProperty.call(__courseCriteriaCache, course)) {
		return;
	}

	const res = await frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Course Assessment Criteria",
			fields: ["assessment_criteria"],
			filters: { parent: course },
			limit_page_length: 500
		},
		freeze: false
	});

	__courseCriteriaCache[course] = (res.message || [])
		.map(r => r.assessment_criteria)
		.filter(Boolean);
}

function set_assessment_criteria_query(frm) {
	frm.set_query("assessment_criteria", "assessment_criteria", () => {
		const course = (frm.doc.course || "").trim();
		const allowed = course && __courseCriteriaCache[course]
			? __courseCriteriaCache[course]
			: [];

		// If no course or no allowed criteria, hide everything
		if (!course || !allowed.length) {
			return {
				filters: { name: ["=", "__none__"] }
			};
		}

		return {
			filters: {
				name: ["in", allowed]
			}
		};
	});
}


// ----------------- Auto load (add-only) & rubric seeding -------------------
function should_sync_students(doc) {
	return !!doc.student_group && !!(doc.points || doc.criteria || doc.binary || doc.observations);
}

async function ensure_saved_then(fn, frm) {
	// Save if new or dirty, then call fn again on the fresh doc
	if (frm.is_new() || frm.is_dirty()) {
		await frm.save();
	}
	await fn(frm);
}

async function auto_sync_students_if_needed(frm) {
	if (!should_sync_students(frm.doc)) return;
	// Avoid auto-saving when Criteria is ON but no Assessment Criteria rows yet;
	// server-side validation would fail and spam errors.
	if (frm.doc.criteria && !has_any_criteria(frm)) return;

	// Brand-new or unsaved changes → save first so we have a real DB row
	if (frm.is_new() || frm.is_dirty()) {
		return ensure_saved_then(auto_sync_students_if_needed, frm);
	}

	try {
		const res = await frappe.call({
			method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_students",
			args: { task: frm.doc.name },   // now a real Task name
			freeze: false,
		});

		if (res?.message?.inserted > 0) {
			frappe.show_alert({
				message: __("{0} students added from group.", [res.message.inserted]),
				indicator: "green",
			});
			await frm.reload_doc();
		}
	} catch (e) {
		console.error(e);
	}
}
async function auto_seed_rubrics_if_needed(frm) {
	// Only relevant when:
	// - Criteria grading is ON
	// - The Task is saved (has a name)
	// - There are Task Student rows
	// - There are Assessment Criteria rows
	// - There are currently NO rubric rows (Task Criterion Score is empty)
	if (!frm.doc.criteria) return;
	if (!frm.doc.name) return;

	const hasStudents = (frm.doc.task_student || []).length > 0;
	if (!hasStudents) return;

	const hasCriteriaRows = has_any_criteria(frm);
	if (!hasCriteriaRows) return;

	const hasRubricRows = (frm.doc.task_criterion_score || []).length > 0;
	if (hasRubricRows) return; // already seeded once; avoid extra calls

	try {
		const res = await frappe.call({
			method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_rubrics",
			args: { task: frm.doc.name },
			freeze: false,
		});

		if (res?.message?.created > 0) {
			frappe.show_alert({
				message: __("{0} rubric cells prepared for criteria grading.", [res.message.created]),
				indicator: "blue",
			});
			await frm.reload_doc();
		}
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

	const course = (frm.doc.course || "").trim();
	if (!course) return;

	// If we've already tried for this course (including NONE / ERROR), don't hammer the server
	if (Object.prototype.hasOwnProperty.call(__gradeScaleCache, course)) {
		const cached = __gradeScaleCache[course];

		// Only auto-fill when we have a real grade scale name
		if (cached && cached !== "__NONE__" && cached !== "__ERROR__") {
			await frm.set_value("grade_scale", cached);
			frappe.show_alert({
				message: __("Loaded default grade scale from Course"),
				indicator: "blue",
			});
		}
		return;
	}

	try {
		const r = await frappe.db.get_value("Course", course, "default_grade_scale");
		const gs = r?.message?.default_grade_scale || null;

		// Cache outcome so we don't keep calling
		if (gs) {
			__gradeScaleCache[course] = gs;
			await frm.set_value("grade_scale", gs);
			frappe.show_alert({
				message: __("Loaded default grade scale from Course"),
				indicator: "blue",
			});
		} else {
			// No default on this course → remember that and stop retrying
			__gradeScaleCache[course] = "__NONE__";
		}
	} catch (e) {
		console.error("Failed to load default grade scale for course", course, e);
		// Mark as error so we do NOT keep retrying every time UI refreshes
		__gradeScaleCache[course] = "__ERROR__";
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

		let label = fieldname;
		const df = frappe.meta.get_docfield(cdt, fieldname, frm.doc.name);
		if (df && df.label) {
			label = df.label;
		}

		frappe.show_alert({
			message: __("{0} adjusted to stay within 0 and Task Max Points.", [label]),
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
function prevent_duplicate_task_student(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.student) {
		return;
	}

	const all_rows = frm.doc.task_student || [];
	const same_student_rows = all_rows.filter(r => r.student === row.student);

	if (same_student_rows.length > 1) {
		frappe.msgprint({
			title: __('Duplicate Student'),
			message: __('This student is already in the Task Student table. Each student can only appear once.'),
			indicator: 'orange'
		});

		frappe.model.set_value(cdt, cdn, 'student', null);
	}
}
