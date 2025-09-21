// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt


// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// --- Helpers ---------------------------------------------------------------

function set_term_field_queries(frm) {
	["term_start", "term_end"].forEach((field) => {
		frm.set_query(field, "courses", async function () {
			if (frm.doc.school && frm.doc.academic_year) {
				const res = await frappe.call({
					method: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_valid_terms_with_fallback",
					args: {
						school: frm.doc.school,
						academic_year: frm.doc.academic_year
					}
				});
				const data = res.message || {};
				if (data.valid_terms && data.valid_terms.length) {
					return { filters: [["Term", "name", "in", data.valid_terms]] };
				}
			}
			// No valid terms available for the context → return empty set
			return { filters: [["Term", "name", "=", "___NONE___"]] };
		});
	});
}

function set_queries(frm) {
	// Optional convenience: filter Program Offering by Program (if user preselects a program)
	frm.set_query("program_offering", () => {
		const filters = {};
		if (frm.doc.program) filters.program = frm.doc.program;
		return { filters };
	});

	// Academic Year: restrict to the offering’s AY spine (client-side)
	frm.set_query("academic_year", () => {
		if (Array.isArray(frm._off_ay_names) && frm._off_ay_names.length) {
			return { filters: { name: ["in", frm._off_ay_names] } };
		}
		return {};
	});

	// Courses grid: only courses defined on the selected Program Offering
	frm.fields_dict.courses.grid.get_field("course").get_query = function () {
		if (!frm.doc.program_offering) return {};
		return {
			query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_program_courses",
			filters: { program_offering: frm.doc.program_offering }
		};
	};

	// Term fields: rely on the richer fallback helper (set via set_term_field_queries)
	// (No extra term query here to avoid duplication/conflicts.)
}

function load_offering_ay_spine(frm) {
	if (!frm.doc.program_offering) {
		frm._off_ay_names = [];
		frm._off_ay_bounds = null;
		return Promise.resolve();
	}
	return frappe.call({
		method: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_offering_ay_spine",
		args: { offering: frm.doc.program_offering }
	}).then(r => {
		const rows = r.message || [];
		frm._off_ay_names = rows.map(x => x.academic_year);
		frm._off_ay_bounds = rows.length
			? { start: rows[0].year_start_date, end: rows[rows.length - 1].year_end_date }
			: null;
	});
}


function show_offering_span_indicator(frm) {
	if (!frm._off_ay_bounds) return;
	const s = frm._off_ay_bounds.start, e = frm._off_ay_bounds.end;
	if (!s || !e) return;
	frm.dashboard.clear_headline();
	frm.dashboard.set_headline(__("Offering window: {0} → {1}", [
		frappe.format(s, { fieldtype: "Date" }),
		frappe.format(e, { fieldtype: "Date" })
	]));
}

// --- Main form events ------------------------------------------------------

frappe.ui.form.on("Program Enrollment", {
	onload(frm) {
		set_queries(frm);
		set_term_field_queries(frm);
		// Grid UX
		frm.get_field("courses").grid.set_multiple_add("course");
	},

	refresh(frm) {
		set_queries(frm);
		show_offering_span_indicator(frm);
	},

	// Offering is the source of truth for school/cohort and AY spine.
	program_offering: frappe.utils.debounce(function (frm) {
		if (!frm.doc.program_offering) return;

		frappe.db.get_value("Program Offering", frm.doc.program_offering,
			["program", "school", "student_cohort"])
			.then(({ message }) => {
				if (!message) return;
				// Program is still present on Enrollment for now; set if empty
				if (!frm.doc.program && message.program) frm.set_value("program", message.program);
				// Always mirror school/cohort from offering
				if (message.school) frm.set_value("school", message.school);
				if (message.student_cohort) frm.set_value("cohort", message.student_cohort);
			})
			.then(() => load_offering_ay_spine(frm))
			.then(() => {
				// If offering has exactly one AY, auto-pick it when empty
				if (!frm.doc.academic_year && Array.isArray(frm._off_ay_names) && frm._off_ay_names.length === 1) {
					frm.set_value("academic_year", frm._off_ay_names[0]);
				}
				// Seed required courses from the offering if currently empty
				if (!frm.doc.courses || frm.doc.courses.length === 0) {
					frm.call("get_courses").then(r => {
						const rows = (r && r.message) || [];
						if (rows.length) {
							frm.clear_table("courses");
							rows.forEach(row => frm.add_child("courses", row));
							frm.refresh_field("courses");
						}
					});
				}
				show_offering_span_indicator(frm);
			});
	}, 200),

	academic_year(frm) {
		show_offering_span_indicator(frm);
	},

	// Keep this—now calls the server method that seeds from Program Offering Course
	get_courses(frm) {
		frm.set_value("courses", []);
		frappe.call({
			method: "get_courses",
			doc: frm.doc,
			callback: function (r) {
				if (r.message) frm.set_value("courses", r.message);
			}
		});
	}
});

// Child table event: when picking a course, set defaults for non-term-long courses
frappe.ui.form.on("Program Enrollment Course", {
	async course(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);

		// 1) Default status
		if (!row.status) frappe.model.set_value(cdt, cdn, "status", "Enrolled");

		// 2) For non-term-long courses, default term range to AY bounds (via helper)
		if (row.course && frm.doc.school && frm.doc.academic_year) {
			const course = await frappe.db.get_doc("Course", row.course);
			if (!course.term_long) {
				frm.term_bounds_cache = frm.term_bounds_cache || {};

				if (!frm.term_bounds_cache[frm.doc.school]) {
					const res = await frappe.call({
						method: "ifitwala_ed.schedule.schedule_utils.get_school_term_bounds",
						args: { school: frm.doc.school, academic_year: frm.doc.academic_year }
					});
					frm.term_bounds_cache[frm.doc.school] = res.message || {};
				}

				const bounds = frm.term_bounds_cache[frm.doc.school];
				if (bounds.term_start && bounds.term_end) {
					frappe.model.set_value(cdt, cdn, "term_start", bounds.term_start);
					frappe.model.set_value(cdt, cdn, "term_end", bounds.term_end);
				} else {
					// Fallback: first and last term in AY
					const terms = await frappe.db.get_list("Term", {
						filters: { school: frm.doc.school, academic_year: frm.doc.academic_year },
						fields: ["name", "term_start_date", "term_end_date"],
						order_by: "term_start_date asc"
					});
					if (terms.length) {
						frappe.model.set_value(cdt, cdn, "term_start", terms[0].name);
						frappe.model.set_value(cdt, cdn, "term_end", terms[terms.length - 1].name);
					}
				}
			}
		}
	}
});
