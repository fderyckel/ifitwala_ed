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
		auto_sync_students_if_needed(frm);
	},

	max_points(frm) {
		// Only in points-only mode
		if (!frm.doc.points || frm.doc.criteria) return;

		const cap = Number(frm.doc.max_points || 0);
		const rows = frm.doc.task_student || [];

		for (const row of rows) {
			const cdt = row.doctype;
			const cdn = row.name;

			// Mirror out_of
			frappe.model.set_value(cdt, cdn, "out_of", cap || 0);

			// If mark is empty or no denominator → clear pct
			if (
				row.mark_awarded === null ||
				row.mark_awarded === "" ||
				row.mark_awarded === undefined ||
				!cap
			) {
				frappe.model.set_value(cdt, cdn, "pct", null);
				continue;
			}

			const mark = Number(row.mark_awarded);
			if (Number.isNaN(mark)) {
				frappe.model.set_value(cdt, cdn, "pct", null);
				continue;
			}

			frappe.model.set_value(cdt, cdn, "pct", (mark / cap) * 100);
		}

		frm.refresh_field("task_student");
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

	mark_awarded(frm, cdt, cdn) {
		clamp_mark_awarded(frm, cdt, cdn);
		sync_points_totals_for_row(frm, cdt, cdn);
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
    // Only sync when student_group exists AND some grading mode is enabled
    if (!should_sync_students(frm.doc)) return;

    // Safety: Task must be saved
    if (frm.is_new() || frm.is_dirty()) {
        frappe.show_alert({
            message: __("Save the Task first, then students will be loaded from the group."),
            indicator: "orange",
        });
        return;
    }

    // Do not run multiple syncs concurrently
    if (frm.__student_sync_in_progress) return;
    frm.__student_sync_in_progress = true;

    try {
        // Before syncing, capture current student list
        const existingStudents = new Set(
            (frm.doc.task_student || []).map(r => r.student)
        );

        // Ask server for missing students only
        const res = await frappe.call({
            method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_students",
            args: { task: frm.doc.name },
            freeze: false,
        });

        const inserted = res?.message?.inserted || 0;

        if (inserted > 0) {
            frappe.show_alert({
                message: __("{0} students added from group.", [inserted]),
                indicator: "green",
            });
            await frm.reload_doc();
        }

    } catch (e) {
        console.error("Student sync failed:", e);

    } finally {
        frm.__student_sync_in_progress = false;
    }
}




async function auto_seed_rubrics_if_needed(frm) {
    // Criteria must be ON
    if (!frm.doc.criteria) return;

    // Only run when Task is saved
    if (!frm.doc.name) return;

    // Require students
    const studentRows = frm.doc.task_student || [];
    if (studentRows.length === 0) return;

    // Require criteria rows
    const criteriaRows = frm.doc.assessment_criteria || [];
    const hasCriteria = criteriaRows.some(r => r.assessment_criteria);
    if (!hasCriteria) return;

    // If ANY rubric row already exists → do NOT seed.
    const rubricRows = frm.doc.task_criterion_score || [];
    if (rubricRows.length > 0) return;

    // Protect against rapid double-trigger from refresh/save
    if (frm.__rubric_prefill_in_progress) return;

    frm.__rubric_prefill_in_progress = true;

    try {
        const res = await frappe.call({
            method: "ifitwala_ed.assessment.doctype.task.task.prefill_task_rubrics",
            args: { task: frm.doc.name },
            freeze: false,
        });

        const created = res?.message?.created || 0;

        if (created > 0) {
            frappe.show_alert({
                message: __("{0} rubric cells prepared for criteria grading.", [created]),
                indicator: "blue",
            });
            await frm.reload_doc();
        }

    } catch (e) {
        console.error("Rubric prefill failed:", e);

    } finally {
        frm.__rubric_prefill_in_progress = false;
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
    // Clamp ONLY in points mode and ONLY when NOT using criteria
    if (!frm.doc.points || frm.doc.criteria) return;

    const cap = Number(frm.doc.max_points || 0);
    const d = frappe.get_doc(cdt, cdn);

    let v = Number(d.mark_awarded || 0);
    if (Number.isNaN(v)) v = 0;

    // Clamp between 0 and cap (cap may be 0 → allow only ≥0)
    let clamped = cap > 0 ? Math.min(Math.max(0, v), cap) : Math.max(0, v);

    if (clamped !== v) {
        frappe.model.set_value(cdt, cdn, "mark_awarded", clamped);
        frappe.show_alert({
            message: __("Adjusted to stay within 0 and Max Points."),
            indicator: "orange"
        });
    }
}

function sync_points_totals_for_row(frm, cdt, cdn) {
	// Only in points-only mode (points ON, criteria OFF)
	if (!frm.doc.points || frm.doc.criteria) return;

	const cap = Number(frm.doc.max_points || 0);
	const row = frappe.get_doc(cdt, cdn);

	// Always mirror out_of to max_points (or 0 if unset)
	frappe.model.set_value(cdt, cdn, "out_of", cap || 0);

	// If no mark entered → clear pct
	if (
		row.mark_awarded === null ||
		row.mark_awarded === "" ||
		row.mark_awarded === undefined
	) {
		frappe.model.set_value(cdt, cdn, "pct", null);
		return;
	}

	const mark = Number(row.mark_awarded);
	if (Number.isNaN(mark) || !cap) {
		// Non-numeric mark or zero denominator → no pct
		frappe.model.set_value(cdt, cdn, "pct", null);
		return;
	}

	const pct = (mark / cap) * 100;
	frappe.model.set_value(cdt, cdn, "pct", pct);
}


function update_task_student_visibility(frm) {
	const grid = frm.fields_dict?.task_student?.grid;
	if (!grid) return;

	const isBinary = !!frm.doc.binary;
	const isPoints = !!frm.doc.points && !frm.doc.criteria;
	const isCriteria = !!frm.doc.criteria;
	const isObservations = !!frm.doc.observations;

	// Default: hide all optional scoring columns
	grid.set_column_disp("mark_awarded", false);
	grid.set_column_disp("complete", false);
	grid.set_column_disp("out_of", false);
	grid.set_column_disp("pct", false);

	// Apply mode-specific visibility
	if (isBinary) {
		grid.set_column_disp("complete", true);
	}

	else if (isPoints) {
		grid.set_column_disp("mark_awarded", true);
	}

	else if (isCriteria) {
		grid.set_column_disp("out_of", true);
		grid.set_column_disp("pct", true);
	}

	// Observations mode → nothing extra visible

	grid.refresh();
}


function compute_status_preview(frm, row) {

    // ------------------------------------
    // 1. Returned always overrides everything
    // ------------------------------------
    if (row.visible_to_student || row.visible_to_guardian) {
        return "Returned";
    }

    // Normalized common fields
    const feedbackText = (row.feedback || "").trim();
    const hasFeedback = feedbackText.length > 0;
    const isComplete = !!row.complete;

    // ------------------------------------
    // 2. BINARY MODE
    // ------------------------------------
    if (frm.doc.binary) {
        if (isComplete || hasFeedback) return "Graded";
        return "Assigned";
    }

    // ------------------------------------
    // 3. POINTS-ONLY MODE (no criteria)
    // ------------------------------------
    if (frm.doc.points && !frm.doc.criteria) {
        let raw = row.mark_awarded;
        let markNum = (raw === null || raw === "" || raw === undefined)
            ? null
            : Number(raw);

        const hasMarkAwarded =
            markNum !== null && !Number.isNaN(markNum);

        if (hasMarkAwarded || hasFeedback)
            return "Graded";

        return "Assigned";
    }

    // ------------------------------------
    // 4. CRITERIA MODE (rubric-driven)
    // ------------------------------------
    if (frm.doc.criteria) {
        // Collect rubric rows for this student
        const rubricRows = (frm.doc.task_criterion_score || []).filter(
            r => r.student === row.student
        );

        let hasRubricActivity = false;

        for (const r of rubricRows) {
            const hasLevel = !!(r.level && String(r.level).trim());
            const hasPts = Number(r.level_points || 0) !== 0;
            const hasRubricFeedback = (r.feedback || "").trim().length > 0;

            if (hasLevel || hasPts || hasRubricFeedback) {
                hasRubricActivity = true;
                break;
            }
        }

        if (hasRubricActivity || hasFeedback)
            return "Graded";

        return "Assigned";
    }

    // ------------------------------------
    // 5. OBSERVATIONS MODE
    // ------------------------------------
    if (frm.doc.observations) {
        return hasFeedback ? "Graded" : "Assigned";
    }

    // ------------------------------------
    // 6. Fallback
    // ------------------------------------
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
    if (!row.student) return;

    const all = frm.doc.task_student || [];

    // Collect all rows with this student
    const matches = all.filter(r => r.student === row.student);

    // If more than one, this is a duplicate → reject new entry
    if (matches.length > 1) {
        frappe.msgprint({
            title: __("Duplicate Student"),
            message: __("This student already exists in the Task Student table."),
            indicator: "orange"
        });

        frappe.model.set_value(cdt, cdn, "student", null);
    }
}
