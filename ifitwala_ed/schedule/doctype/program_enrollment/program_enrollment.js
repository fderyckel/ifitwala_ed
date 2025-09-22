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
		const q = { filters: {}, order_by: "year_start_date desc" };
		if (Array.isArray(frm._off_ay_names) && frm._off_ay_names.length) {
			q.filters.name = ["in", frm._off_ay_names];
		}
		return q;
	});
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


// --- Duplicate guard: helpers ----------------------------------------------

function build_course_index(frm) {
	// Returns a map: { course_name: [row_idx, ...] }
	const idx = {};
	(frm.doc.courses || []).forEach((r, i) => {
		if (!r.course) return;
		if (!idx[r.course]) idx[r.course] = [];
		idx[r.course].push(i + 1); // 1-based row index for user messages
	});
	return idx;
}

function get_duplicate_courses(frm) {
	const idx = build_course_index(frm);
	const dups = Object.entries(idx).filter(([, rows]) => rows.length > 1);
	return dups.map(([course, rows]) => ({ course, rows }));
}

function clear_if_duplicate(frm, cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	if (!row.course) return;

	const dups = get_duplicate_courses(frm);
	const hit = dups.find(d => d.course === row.course);
	if (!hit) return;

	// If duplicate: clear the NEW assignment (assume the latest change is the new one)
	frappe.show_alert({ message: __("Course already added (row(s): {0}).", [hit.rows.join(", ")]), indicator: "orange" });
	frappe.model.set_value(cdt, cdn, "course", "");
}


// --- New helpers: inline row validation ------------------------------------

async function get_term_meta_cached(frm, term_name) {
	frm._term_meta_cache = frm._term_meta_cache || {};
	if (frm._term_meta_cache[term_name]) return frm._term_meta_cache[term_name];

	// Fetch minimal fields we need; cache the result
	const meta = await frappe.db.get_value(
		"Term",
		term_name,
		["academic_year", "term_start_date", "term_end_date"]
	);
	const m = (meta && meta.message) || {};
	frm._term_meta_cache[term_name] = {
		academic_year: m.academic_year || null,
		start: m.term_start_date || null,
		end: m.term_end_date || null
	};
	return frm._term_meta_cache[term_name];
}

function set_parent_warning_banner(frm) {
	const has_warn = (frm._row_warnings || 0) > 0;
	frm.dashboard.clear_comment();
	if (has_warn) {
		frm.dashboard.set_comment(
			__("Some course rows need attention (term order / AY mismatch). Review before saving."),
			"yellow"
		);
	}
}

async function validate_row_terms(frm, row) {
	// Reset form-level counter on first call of a validation burst
	if (!frm._validating_rows) {
		frm._validating_rows = true;
		frm._row_warnings = 0;
	}

	let warned = false;

	// Quick skip: nothing to validate if neither term set
	if (!row.term_start && !row.term_end) return;

	// Load term metas (cached)
	const tStart = row.term_start ? await get_term_meta_cached(frm, row.term_start) : null;
	const tEnd   = row.term_end   ? await get_term_meta_cached(frm, row.term_end)   : null;

	// 1) Term order: end >= start (only when both present and both have dates)
	if (tStart && tEnd && tStart.start && tEnd.end) {
		// Compare by string dates is safe in ISO format; if unsure, use moment
		if (tEnd.end < tStart.start) {
			frappe.show_alert({ message: __("Row: Term End is before Term Start."), indicator: "orange" });
			warned = true;
		}
	}

	// 2) Term within selected AY (if AY chosen on parent)
	if (frm.doc.academic_year) {
		if (tStart && tStart.academic_year && tStart.academic_year !== frm.doc.academic_year) {
			frappe.show_alert({ message: __("Row: Term Start is not in selected Academic Year."), indicator: "orange" });
			warned = true;
		}
		if (tEnd && tEnd.academic_year && tEnd.academic_year !== frm.doc.academic_year) {
			frappe.show_alert({ message: __("Row: Term End is not in selected Academic Year."), indicator: "orange" });
			warned = true;
		}
	}

	// 3) Term within Offering AY spine (always check if we have it)
	// frm._off_ay_names is populated by load_offering_ay_spine()
	if (Array.isArray(frm._off_ay_names) && frm._off_ay_names.length) {
		if (tStart && tStart.academic_year && !frm._off_ay_names.includes(tStart.academic_year)) {
			frappe.show_alert({ message: __("Row: Term Start AY is not part of the Program Offering span."), indicator: "orange" });
			warned = true;
		}
		if (tEnd && tEnd.academic_year && !frm._off_ay_names.includes(tEnd.academic_year)) {
			frappe.show_alert({ message: __("Row: Term End AY is not part of the Program Offering span."), indicator: "orange" });
			warned = true;
		}
	}

	if (warned) frm._row_warnings++;

	// After a short debounce window, update the parent banner and clear the burst flag
	clearTimeout(frm._validating_rows_timer);
	frm._validating_rows_timer = setTimeout(() => {
		set_parent_warning_banner(frm);
		frm._validating_rows = false;
	}, 150);
}

function warn_if_enrollment_date_outside_offering(frm) {
	if (!frm._off_ay_bounds || !frm.doc.enrollment_date) return;
	const s = frm._off_ay_bounds.start, e = frm._off_ay_bounds.end;
	if (!s || !e) return;
	const d = frm.doc.enrollment_date;
	if (d < s || d > e) {
		frappe.show_alert({
			message: __("Enrollment Date is outside the Program Offering window."),
			indicator: "orange"
		});
	}
}



function enforce_dropped_requires_date(frm, row) {
	if (row.status === "Dropped" && !row.dropped_date) {
		frappe.show_alert({
			message: __("Please set a Dropped Date for dropped courses."),
			indicator: "orange"
		});
	}
}


function open_add_from_offering_dialog(frm) {
	if (!frm.doc.program_offering || !frm.doc.academic_year) {
		frappe.msgprint({
			title: __("Select Offering & Academic Year"),
			message: __("Please choose a Program Offering and an Academic Year first."),
			indicator: "orange"
		});
		return;
	}

	const existing = (frm.doc.courses || []).map(r => r.course).filter(Boolean);

	frappe.call({
		method: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.candidate_courses_for_add_multiple",
		args: {
			program_offering: frm.doc.program_offering,
			academic_year: frm.doc.academic_year,
			existing: existing
		}
	}).then(r => {
		const rows = r.message || [];
		if (!rows.length) {
			frappe.msgprint({
				title: __("No Candidates"),
				message: __("All offering courses overlapping this Academic Year are already added."),
				indicator: "green"
			});
			return;
		}

		const d = new frappe.ui.Dialog({
			title: __("Add Courses from Offering"),
			size: "large",
			fields: [
				{
					fieldname: "filter",
					fieldtype: "Data",
					label: __("Filter"),
					description: __("Type to filter the list below"),
					change: () => {
						const q = (d.get_value("filter") || "").toLowerCase();
						d.get_field("picker_html").$wrapper.find(".pe-pick-row").each(function () {
							const txt = (this.getAttribute("data-text") || "").toLowerCase();
							this.style.display = txt.includes(q) ? "" : "none";
						});
					}
				},
				{ fieldname: "picker_html", fieldtype: "HTML" }
			],
			primary_action_label: __("Add Selected"),
			primary_action: () => {
				const selected = [];
				d.get_field("picker_html").$wrapper.find("input[type=checkbox].pe-pick").each(function () {
					if (this.checked) selected.push(this.value);
				});
				if (!selected.length) {
					frappe.show_alert({ message: __("Nothing selected."), indicator: "orange" });
					return;
				}

				const existingSet = new Set((frm.doc.courses || []).map(r => r.course).filter(Boolean));
				let added = 0;

				selected.forEach(name => {
					if (existingSet.has(name)) return;
					const info = rows.find(r => r.course === name);
					const child = frm.add_child("courses", {
						course: name,
						status: "Enrolled"
					});
					if (info && info.suggested_term_start) child.term_start = info.suggested_term_start;
					if (info && info.suggested_term_end) child.term_end = info.suggested_term_end;
					added++;
				});

				frm.refresh_field("courses");
				d.hide();
				frappe.show_alert({ message: __("Added {0} course(s).", [added]), indicator: "green" });
			}
		});

		const html = `
			<div class="pe-pick-list" style="max-height: 50vh; overflow:auto; border:1px solid var(--border-color); border-radius: .5rem;">
				${rows.map(r => {
					const label = frappe.utils.escape_html(r.course_name || r.course);
					const small = r.required ? `<span class="badge bg-warning text-dark" style="margin-left:.5rem;">${__("Required")}</span>` : "";
					const helper = (r.suggested_term_start || r.suggested_term_end)
						? `<div class="text-muted small">${__("Suggested terms")}: ${(r.suggested_term_start || "—")} → ${(r.suggested_term_end || "—")}</div>`
						: "";
					return `
						<label class="pe-pick-row list-group-item d-flex align-items-start gap-2"
						       data-text="${frappe.utils.escape_html((r.course || "") + " " + (r.course_name || ""))}">
							<input type="checkbox" class="form-check-input pe-pick" value="${frappe.utils.escape_html(r.course)}" />
							<div>
								<div><strong>${label}</strong>${small}</div>
								${helper}
							</div>
						</label>
					`;
				}).join("")}
			</div>
		`;
		d.get_field("picker_html").$wrapper.html(html);
		d.show();
	});
}

function add_grid_actions(frm) {
	const grid = frm.fields_dict.courses?.grid;
	if (!grid) return;
	if (grid._add_from_offering_btn) return; // idempotent
	grid._add_from_offering_btn = true;

	grid.add_custom_button(__("Add from Offering…"), () => open_add_from_offering_dialog(frm));
}



// --- Main form events ------------------------------------------------------

frappe.ui.form.on("Program Enrollment", {
	onload(frm) {
		set_queries(frm);
		set_term_field_queries(frm);
	},

	refresh(frm) {
		set_queries(frm);
		show_offering_span_indicator(frm);
		warn_if_enrollment_date_outside_offering(frm); 
		add_grid_actions(frm);
	},

	before_save(frm) {
		// Consolidate warnings discovered during row-level checks (Change 1).
		if (frm._row_warnings && frm._row_warnings > 0) {
			frappe.msgprint({
				title: __("Review course rows"),
				message: __(
					"{0} potential issue(s) were detected (e.g., term order or AY mismatch). You can still save, but please review.",
					[frm._row_warnings]
				),
				indicator: "yellow"
			});
		}

		const missing = (frm.doc.courses || []).filter(r => r.status === "Dropped" && !r.dropped_date);
		if (missing.length) {
			frappe.msgprint({
				title: __("Dropped courses missing dates"),
				message: __("{0} row(s) marked Dropped have no Dropped Date. Please add dates.", [missing.length]),
				indicator: "yellow"
			});
		}

		const idx = {};
		(frm.doc.courses || []).forEach((r, i) => {
			if (!r.course) return;
			(idx[r.course] ||= []).push(i + 1);
		});
		const dupLines = Object.entries(idx)
			.filter(([, rows]) => rows.length > 1)
			.map(([course, rows]) => `• ${course} — rows ${rows.join(", ")}`);
		if (dupLines.length) {
			frappe.throw({
				title: __("Duplicate Courses in Enrollment"),
				message: __(
					"Each course can only appear once. Please resolve:<br><br>{0}",
					[`<div style='margin-left:.5rem'>${dupLines.join("<br>")}</div>`]
				)
			});
		}
	}, 

	enrollment_date(frm) {
		warn_if_enrollment_date_outside_offering(frm);
	},

	program(frm) {
		if (Array.isArray(frm.doc.courses) && frm.doc.courses.length > 0) {
			const old_len = frm.doc.courses.length;
			frm.clear_table("courses");
			frm.refresh_field("courses");
			frappe.show_alert({
				message: __("{0} course row(s) cleared because Program changed.", [old_len]),
				indicator: "orange"
			});
		}
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
				warn_if_enrollment_date_outside_offering(frm); 
			});
	}, 200),

	academic_year(frm) {
		show_offering_span_indicator(frm);
		warn_if_enrollment_date_outside_offering(frm); 
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

		clear_if_duplicate(frm, cdt, cdn);
		if (!row.course) return;

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
		
		await validate_row_terms(frm, row);

	}, 

 	status(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		enforce_dropped_requires_date(frm, row);
	},

	dropped_date(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		enforce_dropped_requires_date(frm, row);
	}, 

	async term_start(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		await validate_row_terms(frm, row);
	},

	async term_end(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		await validate_row_terms(frm, row);
	}
});
