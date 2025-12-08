// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/assessment/doctype/task/task.js

frappe.ui.form.on("Task", {
	setup(frm) {
			// Existing setup logic
			set_learning_unit_query(frm);
			set_lesson_query(frm);
			make_is_graded_readonly(frm);

			// Prevent duplicate Assessment Criteria rows on the Task itself
			const table = frm.fields_dict.assessment_criteria;
			if (table && table.grid) {
					table.grid
							.get_field("assessment_criteria")
							.get_query = function (doc, cdt, cdn) {
									const selected = (doc.assessment_criteria || [])
											.map(row => row.assessment_criteria)
											.filter(v => !!v);

									const filters = [];
									if (selected.length) {
											filters.push(["Assessment Criteria", "name", "not in", selected]);
									}

									return { filters };
							};
			}
	},

	refresh(frm) {
		derive_is_graded(frm);
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		update_task_student_visibility(frm);
		enforce_total_mark_hidden(frm);
		ensure_points_field_rules(frm);       // show/require max_points only when points==1
		auto_sync_students_if_needed(frm);    // add-only; no removals
		auto_seed_rubrics_if_needed(frm);     // if criteria==1 and students exist

	},

	after_save(frm) {
		// Keep this light; no network calls here
		derive_is_graded(frm);
		set_learning_unit_query(frm);
		set_lesson_query(frm);
		ensure_points_field_rules(frm);
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
			//ensure_default_grade_scale(frm);   // allowed here
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
		//ensure_default_grade_scale(frm);
	},

	learning_unit(frm) {
		if (frm.doc.lesson) frm.set_value("lesson", null);
		set_lesson_query(frm);
	},

	// --- grading toggles ----------------------------------------------------
	binary(frm) {
		derive_is_graded(frm);
		enforce_total_mark_hidden(frm);
		update_task_student_visibility(frm);
		auto_sync_students_if_needed(frm);
	},

	observations(frm) {
		derive_is_graded(frm);
		enforce_total_mark_hidden(frm);
		auto_sync_students_if_needed(frm);
	},

	points(frm) {
		derive_is_graded(frm);
		ensure_points_field_rules(frm);
		enforce_total_mark_hidden(frm);
		auto_sync_students_if_needed(frm);
	},

	criteria(frm) {
		// Always keep is_graded in sync
		derive_is_graded(frm);
		enforce_total_mark_hidden(frm);

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

	mark_awarded(frm, cdt, cdn) {
		clamp_mark_awarded(frm, cdt, cdn);
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
	// -------------------------------
	// Check Task Student rows
	// -------------------------------
	for (const row of (frm.doc.task_student || [])) {

		const has_mark_awarded =
			row.mark_awarded !== undefined &&
			row.mark_awarded !== null &&
			row.mark_awarded !== "";

		// total_mark is deprecated → DO NOT USE IT ANYMORE

		const has_feedback =
			(row.feedback || "").trim().length > 0;

		const has_flags =
			!!(row.complete || row.visible_to_student || row.visible_to_guardian);

		const status = row.status || "";

		// If any actual grading activity is detected
		if (
			has_mark_awarded ||
			has_feedback ||
			has_flags ||
			(status && status !== "Assigned")
		) {
			return true;
		}
	}

	// -------------------------------
	// Check rubric rows (criteria mode)
	// -------------------------------
	for (const r of (frm.doc.task_criterion_score || [])) {
		const hasLevel = !!(r.level && String(r.level).trim());
		const pts = Number(r.level_points || 0);
		const hasRubricFeedback = (r.feedback || "").trim().length > 0;

		if (hasLevel || pts !== 0 || hasRubricFeedback) {
			return true;
		}
	}

	// -------------------------------
	// Otherwise → no grading started
	// -------------------------------
	return false;
}


function make_is_graded_readonly(frm) {
	frm.set_df_property("is_graded", "read_only", 1);
}

function derive_is_graded(frm) {
	// Any of the grading toggles makes the Task graded
	const enabled = !!(frm.doc.points || frm.doc.criteria || frm.doc.binary || frm.doc.observations);

	// Normalise current value to strict 0/1 integer
	const current = frm.doc.is_graded ? 1 : 0;
	const target = enabled ? 1 : 0;

	// Only touch the field when the effective value actually changes
	if (current !== target) {
		frm.set_value("is_graded", target);
	}
}


function ensure_points_field_rules(frm) {
	const pointsOn = !!frm.doc.points;

	// -------------------------------
	// 1. Show / hide max_points
	// -------------------------------
	frm.set_df_property("max_points", "hidden", !pointsOn);
	frm.set_df_property("max_points", "reqd", pointsOn);

	// When points mode is turned OFF → do NOT clear max_points
	// (avoid unnecessary dirty state; server will ignore it anyway)

	// -------------------------------
	// 2. Show / hide grade_scale
	// -------------------------------
	frm.set_df_property("grade_scale", "hidden", !pointsOn);
	frm.set_df_property("grade_scale", "reqd", pointsOn);

	// -------------------------------
	// 3. Refresh both fields visibly
	// -------------------------------
	frm.refresh_field("max_points");
	frm.refresh_field("grade_scale");
}



// ----------------- Auto load (add-only) & rubric seeding -------------------
function should_sync_students(doc) {
	return !!doc.student_group && !!(doc.points || doc.criteria || doc.binary || doc.observations);
}


async function auto_sync_students_if_needed(frm) {
	// Only when there is a student_group AND some grading mode is enabled
	if (!should_sync_students(frm.doc)) return;

	// Never auto-save from here; require a clean, saved doc
	if (frm.is_new() || frm.is_dirty()) {
		frappe.show_alert({
			message: __("Save the Task first, then students will be loaded from the group."),
			indicator: "orange",
		});
		return;
	}

	try {
		const res = await frappe.call({
			method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_students",
			args: { task: frm.doc.name },
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

	// If a fetch is already in progress for this form, don't start another
	if (frm.__grade_scale_fetching) {
		return;
	}

	// If we've already resolved this course (including NONE / ERROR), don't hammer server
	if (Object.prototype.hasOwnProperty.call(__gradeScaleCache, course)) {
		const cached = __gradeScaleCache[course];

		// Only auto-fill when we have a real grade scale name
		if (cached && cached !== "__NONE__" && cached !== "__ERROR__") {
			await frm.set_value("grade_scale", cached);
			// no alert needed here; user already saw it once
		}
		return;
	}

	frm.__grade_scale_fetching = true;
	try {
		const r = await frappe.db.get_value("Course", course, "default_grade_scale");
		const gs = r?.message?.default_grade_scale || null;

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
	} finally {
		frm.__grade_scale_fetching = false;
	}
}



// ----------------- Points clamp & visibility & status preview --------------
function has_any_criteria(frm) {
	return Array.isArray(frm.doc.assessment_criteria) &&
		frm.doc.assessment_criteria.some(r => r.assessment_criteria);
}


function clamp_mark_awarded(frm, cdt, cdn) {
	if (!frm.doc.points || frm.doc.criteria) return; // only pure points mode

	const cap = Number(frm.doc.max_points || 0);
	const d = frappe.get_doc(cdt, cdn);

	let v = Number(d.mark_awarded || 0);
	if (Number.isNaN(v)) v = 0;

	let clamped =
		cap > 0 ? Math.min(Math.max(0, v), cap) : Math.max(0, v);

	if (clamped !== v) {
		frappe.model.set_value(cdt, cdn, "mark_awarded", clamped);

		frappe.show_alert({
			message: __("Adjusted to stay within 0 and Max Points."),
			indicator: "orange",
		});
	}
}





function update_task_student_visibility(frm) {
	const grid = frm.fields_dict?.task_student?.grid;
	if (!grid) return;

	const isPoints = !!frm.doc.points;

	// Points Mode → hide total_mark
	grid.set_column_disp("total_mark", !isPoints);

	// Binary mode → show complete flag
	grid.set_column_disp("complete", !!frm.doc.binary);

	grid.refresh();
}



function compute_status_preview(frm, row) {
	// -------------------------------------
	// 1) Visibility always overrides everything
	// -------------------------------------
	if (row.visible_to_student || row.visible_to_guardian) {
		return "Returned";
	}

	const feedbackText = (row.feedback || "").trim();
	const hasFeedback = feedbackText.length > 0;
	const isComplete = !!row.complete;

	// -------------------------------------
	// 2) BINARY MODE
	// -------------------------------------
	if (frm.doc.binary) {
		// Only completion or feedback matters
		if (isComplete || hasFeedback) return "Graded";
		return "Assigned";
	}

	// -------------------------------------
	// 3) POINTS-ONLY MODE (NO CRITERIA)
	// -------------------------------------
	if (frm.doc.points && !frm.doc.criteria) {
		let raw = row.mark_awarded;
		let markNum =
			raw === null || raw === undefined || raw === ""
				? null
				: Number(raw);

		const hasMarkAwarded =
			markNum !== null && !Number.isNaN(markNum);

		if (hasMarkAwarded || hasFeedback) return "Graded";
		return "Assigned";
	}

	// -------------------------------------
	// 4) CRITERIA / RUBRIC MODE
	// -------------------------------------
	if (frm.doc.criteria) {
		// All rubric rows for this student
		const rubricRows = (frm.doc.task_criterion_score || []).filter(
			r => r.student === row.student
		);

		let hasRubric = false;

		for (const r of rubricRows) {
			const hasLevel = !!(r.level && String(r.level).trim());
			const hasPoints = Number(r.level_points || 0) !== 0;
			const hasRubricFeedback = (r.feedback || "").trim().length > 0;

			if (hasLevel || hasPoints || hasRubricFeedback) {
				hasRubric = true;
				break;
			}
		}

		if (hasRubric || hasFeedback) return "Graded";
		return "Assigned";
	}

	// -------------------------------------
	// 5) OBSERVATIONS-ONLY MODE
	// -------------------------------------
	if (frm.doc.observations) {
		if (hasFeedback) return "Graded";
		return "Assigned";
	}

	// -------------------------------------
	// 6) DEFAULT FALLBACK → Assigned
	// -------------------------------------
	return "Assigned";
}




function enforce_total_mark_hidden(frm) {
	// total_mark does NOT exist on the parent Task, so never touch frm.set_df_property()

	// Hide the total_mark column in the Task Student child table
	const grid = frm.fields_dict?.task_student?.grid;
	if (!grid) return;

	// Always hide total_mark regardless of grading mode
	grid.set_column_disp("total_mark", false);

	// Refresh the grid to apply column visibility
	grid.refresh();
}
function compute_status_preview(frm, row) {
	// -------------------------------------
	// 1) Visibility always overrides everything
	// -------------------------------------
	if (row.visible_to_student || row.visible_to_guardian) {
		return "Returned";
	}

	const feedbackText = (row.feedback || "").trim();
	const hasFeedback = feedbackText.length > 0;
	const isComplete = !!row.complete;

	// -------------------------------------
	// 2) BINARY MODE
	// -------------------------------------
	if (frm.doc.binary) {
		// Only completion or feedback matters
		if (isComplete || hasFeedback) return "Graded";
		return "Assigned";
	}

	// -------------------------------------
	// 3) POINTS-ONLY MODE (NO CRITERIA)
	// -------------------------------------
	if (frm.doc.points && !frm.doc.criteria) {
		let raw = row.mark_awarded;
		let markNum =
			raw === null || raw === undefined || raw === ""
				? null
				: Number(raw);

		const hasMarkAwarded =
			markNum !== null && !Number.isNaN(markNum);

		if (hasMarkAwarded || hasFeedback) return "Graded";
		return "Assigned";
	}

	// -------------------------------------
	// 4) CRITERIA / RUBRIC MODE
	// -------------------------------------
	if (frm.doc.criteria) {
		// All rubric rows for this student
		const rubricRows = (frm.doc.task_criterion_score || []).filter(
			r => r.student === row.student
		);

		let hasRubric = false;

		for (const r of rubricRows) {
			const hasLevel = !!(r.level && String(r.level).trim());
			const hasPoints = Number(r.level_points || 0) !== 0;
			const hasRubricFeedback = (r.feedback || "").trim().length > 0;

			if (hasLevel || hasPoints || hasRubricFeedback) {
				hasRubric = true;
				break;
			}
		}

		if (hasRubric || hasFeedback) return "Graded";
		return "Assigned";
	}

	// -------------------------------------
	// 5) OBSERVATIONS-ONLY MODE
	// -------------------------------------
	if (frm.doc.observations) {
		if (hasFeedback) return "Graded";
		return "Assigned";
	}

	// -------------------------------------
	// 6) DEFAULT FALLBACK → Assigned
	// -------------------------------------
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
