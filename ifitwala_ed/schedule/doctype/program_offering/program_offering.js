// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt


/* ---------------- Utilities & tiny cache ---------------- */

function has_child_table(frm, fieldname) {
	return !!(frm.fields_dict[fieldname] && frm.fields_dict[fieldname].grid);
}

function getCache(frm) {
	frm._po_cache = frm._po_cache || { progAbbr: null, orgAbbr: null };
	return frm._po_cache;
}

/* ---------------- Envelope from Table MultiSelect ---------------- */

function get_ay_envelope(frm) {
	const rows = (frm.doc.offering_academic_years || []);
	if (!rows.length) return { minStart: null, maxEnd: null, cohortYear: null };

	const toObj = d => (d ? frappe.datetime.str_to_obj(d) : null);

	const starts = rows.map(r => toObj(r.year_start_date)).filter(Boolean);
	const ends   = rows.map(r => toObj(r.year_end_date)).filter(Boolean);

	const minStart = starts.length ? starts.reduce((a, b) => (a < b ? a : b)) : null;
	const maxEnd   = ends.length   ? ends.reduce((a, b) => (a > b ? a : b)) : null;

	let cohortDate = null;
	if (maxEnd) cohortDate = maxEnd;
	else if (starts.length) cohortDate = starts.reduce((a, b) => (a > b ? a : b));

	return {
		minStart,
		maxEnd,
		cohortYear: cohortDate ? cohortDate.getFullYear() : null
	};
}

function set_head_dates_if_empty(frm) {
	const { minStart, maxEnd } = get_ay_envelope(frm);
	if (!minStart && !maxEnd) return;

	if (!frm.doc.start_date && minStart) {
		frm.set_value("start_date", frappe.datetime.obj_to_str(minStart));
	}
	if (!frm.doc.end_date && maxEnd) {
		frm.set_value("end_date", frappe.datetime.obj_to_str(maxEnd));
	}
}

/* ---------------- Title generation per spec ---------------- */

async function getProgramAbbr(frm) {
	const cache = getCache(frm);
	if (cache.progAbbr) return cache.progAbbr;
	if (!frm.doc.program) return null;

	try {
		const r = await frappe.db.get_value("Program", frm.doc.program, ["program_abbreviation"]);
		cache.progAbbr = r?.message?.program_abbreviation || null;
		return cache.progAbbr;
	} catch {
		return null;
	}
}

async function getOrganizationAbbrFromSchool(frm) {
	const cache = getCache(frm);
	if (cache.orgAbbr) return cache.orgAbbr;
	if (!frm.doc.school) return null;

	try {
		const s = await frappe.db.get_value("School", frm.doc.school, ["organization"]);
		const org = s?.message?.organization;
		if (!org) return null;
		const o = await frappe.db.get_value("Organization", org, ["abbr"]);
		cache.orgAbbr = o?.message?.abbr || null;
		return cache.orgAbbr;
	} catch {
		return null;
	}
}

let _titleTimer = null;
async function suggest_offering_title(frm) {
	// Only suggest if empty; user can override
	if (frm.doc.offering_title) return;

	// Need program, school, and at least one AY row
	const rows = (frm.doc.offering_academic_years || []);
	if (!frm.doc.program || !frm.doc.school || !rows.length) return;

	const [{ cohortYear }, progAbbr, orgAbbr] = await Promise.all([
		get_ay_envelope(frm),
		getProgramAbbr(frm),
		getOrganizationAbbrFromSchool(frm)
	]);

	if (!cohortYear || !progAbbr || !orgAbbr) return;

	clearTimeout(_titleTimer);
	_titleTimer = setTimeout(() => {
		const title = `${orgAbbr} ${progAbbr} Cohort of ${cohortYear}`;
		frm.set_value("offering_title", title);
	}, 150);
}

/* ---------------- AY span badge + warnings ---------------- */

function show_ay_span_badge(frm) {
	const rows = (frm.doc.offering_academic_years || []);
	const names = rows.map(r => r.ay_name || r.section_break_idsl).filter(Boolean);

	let label = "";
	if (names.length === 1) label = `AY: ${frappe.utils.escape_html(names[0])}`;
	if (names.length >= 2) label = `AY: ${frappe.utils.escape_html(names[0])} → ${frappe.utils.escape_html(names[names.length - 1])}`;

	frm.dashboard.clear_headline();
	if (label) {
		frm.dashboard.set_headline(`<span class="badge bg-primary">${label}</span>`);
	}
}

function warn_if_dates_outside_ay(frm) {
	const headStart = frm.doc.start_date ? frappe.datetime.str_to_obj(frm.doc.start_date) : null;
	const headEnd   = frm.doc.end_date   ? frappe.datetime.str_to_obj(frm.doc.end_date)   : null;
	if (!headStart && !headEnd) return;

	const rows = (frm.doc.offering_academic_years || []);
	const ayStarts = rows.map(r => r.year_start_date).filter(Boolean).map(d => frappe.datetime.str_to_obj(d));
	const ayEnds   = rows.map(r => r.year_end_date).filter(Boolean).map(d => frappe.datetime.str_to_obj(d));
	if (!ayStarts.length || !ayEnds.length) return;

	const minAY = ayStarts.reduce((a, b) => (a < b ? a : b));
	const maxAY = ayEnds.reduce((a, b) => (a > b ? a : b));

	const msgs = [];
	if (headStart && headStart < minAY) msgs.push(__("Start Date is before first Academic Year."));
	if (headEnd && headEnd > maxAY) msgs.push(__("End Date is after last Academic Year."));
	if (headStart && headEnd && headStart > headEnd) msgs.push(__("Start Date is after End Date."));

	if (msgs.length) frappe.show_alert({ message: msgs.join(" "), indicator: "orange" }, 6);
}

/* ---------------- Queries (child tables) ---------------- */

function setup_child_queries(frm) {
	// Table MultiSelect: Offering Academic Years
	if (has_child_table(frm, "offering_academic_years")) {
		// Link field is section_break_idsl (AY)
		frm.set_query("section_break_idsl", "offering_academic_years", () => ({ filters: {} }));
	}

	// Offering Courses table: constrain AY/Term options based on selected AYs
	if (has_child_table(frm, "offering_courses")) {
		const ayLinks = (frm.doc.offering_academic_years || [])
			.map(r => r.section_break_idsl)
			.filter(Boolean);

		const ayFilter = ayLinks.length ? { name: ["in", ayLinks] } : {};

		frm.set_query("start_academic_year", "offering_courses", () => ({ filters: ayFilter }));
		frm.set_query("end_academic_year", "offering_courses",   () => ({ filters: ayFilter }));

		frm.set_query("start_academic_term", "offering_courses", (doc, cdt, cdn) => {
			const row = frappe.get_doc(cdt, cdn);
			return row.start_academic_year ? { filters: { academic_year: row.start_academic_year } } : {};
		});
		frm.set_query("end_academic_term", "offering_courses", (doc, cdt, cdn) => {
			const row = frappe.get_doc(cdt, cdn);
			return row.end_academic_year ? { filters: { academic_year: row.end_academic_year } } : {};
		});
	}
}

/* ---------------- Guards (optional niceties) ---------------- */

function find_duplicate(arr) {
	const seen = new Set();
	for (const x of arr) {
		if (seen.has(x)) return x;
		seen.add(x);
	}
	return null;
}

function guard_unique_ays(frm) {
	const ays = (frm.doc.offering_academic_years || [])
		.map(r => r.section_break_idsl)
		.filter(Boolean);

	const dup = find_duplicate(ays);
	if (dup) {
		frappe.msgprint({
			title: __("Duplicate Academic Year"),
			message: __("Academic Year {0} is listed more than once.", [frappe.utils.escape_html(dup)]),
			indicator: "orange"
		});
	}
}

function guard_ay_order_no_overlap(frm) {
	const rows = (frm.doc.offering_academic_years || [])
		.filter(r => r.year_start_date && r.year_end_date)
		.map(r => ({
			name: r.ay_name || r.section_break_idsl,
			start: frappe.datetime.str_to_obj(r.year_start_date),
			end: frappe.datetime.str_to_obj(r.year_end_date)
		}))
		.sort((a, b) => a.start - b.start);

	for (let i = 1; i < rows.length; i++) {
		if (rows[i - 1].end >= rows[i].start) {
			frappe.msgprint({
				title: __("Overlapping Academic Years"),
				message: __("{0} overlaps with {1}.", [
					frappe.utils.escape_html(rows[i - 1].name),
					frappe.utils.escape_html(rows[i].name)
				]),
				indicator: "orange"
			});
			break;
		}
	}
}

function guard_row_spans_inside_head(frm) {
	const headStart = frm.doc.start_date ? frappe.datetime.str_to_obj(frm.doc.start_date) : null;
	const headEnd   = frm.doc.end_date   ? frappe.datetime.str_to_obj(frm.doc.end_date)   : null;
	if (!headStart && !headEnd) return;

	const rows = frm.doc.offering_courses || [];
	for (const r of rows) {
		const rs = r.from_date ? frappe.datetime.str_to_obj(r.from_date) : null;
		const re = r.to_date   ? frappe.datetime.str_to_obj(r.to_date)   : null;
		if (rs && headStart && rs < headStart) {
			frappe.show_alert({ message: __("A course row starts before the Offering Start Date."), indicator: "orange" });
			break;
		}
		if (re && headEnd && re > headEnd) {
			frappe.show_alert({ message: __("A course row ends after the Offering End Date."), indicator: "orange" });
			break;
		}
	}
}

/* ---------------- Form bindings ---------------- */

frappe.ui.form.on("Program Offering", {
	onload(frm) {
		setup_child_queries(frm);
	},
	refresh(frm) {
		setup_child_queries(frm);
		suggest_offering_title(frm);
		show_ay_span_badge(frm);
		set_head_dates_if_empty(frm);
		warn_if_dates_outside_ay(frm);
	},
	program(frm) {
		suggest_offering_title(frm);
	},
	school(frm) {
		setup_child_queries(frm);
		suggest_offering_title(frm);
	},
	start_date(frm) {
		warn_if_dates_outside_ay(frm);
	},
	end_date(frm) {
		warn_if_dates_outside_ay(frm);
	},
	validate(frm) {
		guard_unique_ays(frm);
		guard_ay_order_no_overlap(frm);
		guard_row_spans_inside_head(frm);
	}
});

// Table MultiSelect rows
frappe.ui.form.on("Program Offering Academic Year", {
	section_break_idsl(frm) {
		set_head_dates_if_empty(frm);
		suggest_offering_title(frm);
		warn_if_dates_outside_ay(frm);
	},
	year_start_date(frm) {
		set_head_dates_if_empty(frm);
		warn_if_dates_outside_ay(frm);
	},
	year_end_date(frm) {
		set_head_dates_if_empty(frm);
		warn_if_dates_outside_ay(frm);
	}
});
