// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program Offering", {
	onload(frm) {
		// Limit child table link fields early
		setup_child_queries(frm);
	},

	refresh(frm) {
		setup_child_queries(frm);
		suggest_offering_title(frm);
		show_ay_span_badge(frm);
		warn_if_dates_outside_ay(frm);
	},

	// When key identity fields change, refresh helpers
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
		// Light client-side guards (server enforces strictly)
		guard_unique_ays(frm);
		guard_ay_order_no_overlap(frm);
		guard_row_spans_inside_head(frm);
	}
});

/* ---------- Helpers ---------- */

function setup_child_queries(frm) {
	// AY table: academic_year — no client filter on school; server enforces ancestor-only
	frm.set_query("academic_year", "offering_academic_years", () => {
		return {
			// Optionally pre-filter by the school's tree via a server method.
			// Keeping it simple: user will search; server will validate.
			filters: {}
		};
	});

	// Course rows — ensure AY picker is limited to the AYs listed in the spine
	const ayNames = (frm.doc.offering_academic_years || []).map(r => r.academic_year).filter(Boolean);

	frm.set_query("start_academic_year", "offering_courses", () => ({
		filters: ayNames.length ? { name: ["in", ayNames] } : {}
	}));

	frm.set_query("end_academic_year", "offering_courses", () => ({
		filters: ayNames.length ? { name: ["in", ayNames] } : {}
	}));

	// Terms should match their selected AY; school ancestry is enforced server-side
	frm.set_query("start_term", "offering_courses", (doc, cdt, cdn) => {
		const row = frappe.get_doc(cdt, cdn);
		return row.start_academic_year ? { filters: { academic_year: row.start_academic_year } } : {};
	});
	frm.set_query("end_term", "offering_courses", (doc, cdt, cdn) => {
		const row = frappe.get_doc(cdt, cdn);
		return row.end_academic_year ? { filters: { academic_year: row.end_academic_year } } : {};
	});
}

async function suggest_offering_title(frm) {
  if (frm.doc.offering_title) return;
  const ays = (frm.doc.offering_academic_years || []).map(r => r.academic_year).filter(Boolean);
  if (!frm.doc.program || !frm.doc.school || !ays.length) return;

  const { message } = await frappe.call({
    method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.title_parts",
    args: { program: frm.doc.program, school: frm.doc.school }
  });

  const ayPretty = ays.length === 1 ? ays[0] : `${ays[0]}–${ays[ays.length - 1]}`;
  frm.set_value("offering_title", `${message.prog_label} ${ayPretty} (${message.school_label})`);
}

function show_ay_span_badge(frm) {
	// Show a small indicator of AY span in the form header
	const ays = (frm.doc.offering_academic_years || []).map(r => r.academic_year).filter(Boolean);
	let label = "";
	if (ays.length === 1) label = `AY: ${ays[0]}`;
	if (ays.length >= 2) label = `AY: ${ays[0]} → ${ays[ays.length - 1]}`;

	if (label) {
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(`<span class="badge bg-primary">${frappe.utils.escape_html(label)}</span>`);
	} else {
		frm.dashboard.clear_headline();
	}
}

function warn_if_dates_outside_ay(frm) {
	// Soft warning only; server does hard enforcement
	const headStart = frm.doc.start_date ? frappe.datetime.str_to_obj(frm.doc.start_date) : null;
	const headEnd   = frm.doc.end_date   ? frappe.datetime.str_to_obj(frm.doc.end_date)   : null;

	if (!headStart && !headEnd) return;

	const rows = (frm.doc.offering_academic_years || []).slice();
	if (!rows.length) return;

	// Compute AY envelope from child table (denormalized in UI)
	const ayStarts = rows.map(r => r.year_start_date).filter(Boolean).map(s => frappe.datetime.str_to_obj(s));
	const ayEnds   = rows.map(r => r.year_end_date).filter(Boolean).map(s => frappe.datetime.str_to_obj(s));
	if (!ayStarts.length || !ayEnds.length) return;

	const minAY = ayStarts.reduce((a, b) => a < b ? a : b);
	const maxAY = ayEnds.reduce((a, b) => a > b ? a : b);

	let msgs = [];
	if (headStart && headStart < minAY) msgs.push(__("Start Date is before first Academic Year."));
	if (headEnd && headEnd > maxAY) msgs.push(__("End Date is after last Academic Year."));
	if (headStart && headEnd && headStart > headEnd) msgs.push(__("Start Date is after End Date."));

	if (msgs.length) {
		frappe.show_alert({ message: msgs.join(" "), indicator: "orange" }, 6);
	}
}

function guard_unique_ays(frm) {
	const ays = (frm.doc.offering_academic_years || []).map(r => r.academic_year).filter(Boolean);
	const dup = find_duplicate(ays);
	if (dup) {
		frappe.msgprint({
			title: __("Duplicate Academic Year"),
			message: __("Academic Year {0} is listed more than once.", [frappe.utils.escape_html(dup)]),
			indicator: "orange"
		});
		// not blocking: server will block; this just hints earlier
	}
}

function guard_ay_order_no_overlap(frm) {
	const rows = (frm.doc.offering_academic_years || [])
		.filter(r => r.year_start_date && r.year_end_date)
		.map(r => ({
			name: r.academic_year,
			start: frappe.datetime.str_to_obj(r.year_start_date),
			end: frappe.datetime.str_to_obj(r.year_end_date)
		}))
		.sort((a, b) => a.start - b.start);

	for (let i = 1; i < rows.length; i++) {
		if (rows[i - 1].end >= rows[i].start) {
			frappe.msgprint({
				title: __("Overlapping Academic Years"),
				message: __("{0} overlaps with {1}.", [frappe.utils.escape_html(rows[i - 1].name), frappe.utils.escape_html(rows[i].name)]),
				indicator: "orange"
			});
			break;
		}
	}
}

function guard_row_spans_inside_head(frm) {
	// If head dates exist, warn for any course row outside
	const headStart = frm.doc.start_date ? frappe.datetime.str_to_obj(frm.doc.start_date) : null;
	const headEnd   = frm.doc.end_date   ? frappe.datetime.str_to_obj(frm.doc.end_date)   : null;
	if (!headStart && !headEnd) return;

	const rows = frm.doc.offering_courses || [];
	for (const r of rows) {
		const rs = r.from_date ? frappe.datetime.str_to_obj(r.from_date) : null;
		const re = r.to_date   ? frappe.datetime.str_to_obj(r.to_date)   : null;
		// If explicit dates provided, check against head window
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

/* ---------- small utilities ---------- */

function find_duplicate(arr) {
	const seen = new Set();
	for (const x of arr) {
		if (seen.has(x)) return x;
		seen.add(x);
	}
	return null;
}

function get_program_code_or_name(program) {
	// Try code, then abbreviation, then name
	return frappe.db.get_value("Program", program, ["program_code", "program_abbreviation", "program_name"])
		.then(r => {
			if (!r || !r.message) return program;
			const m = r.message;
			return m.program_code || m.program_abbreviation || m.program_name || program;
		})
		.catch(() => program);
}

function get_school_short_or_name(school) {
	// Try short code, then name
	return frappe.db.get_value("School", school, ["school_short", "school_name"])
		.then(r => {
			if (!r || !r.message) return school;
			const m = r.message;
			return m.school_short || m.school_name || school;
		})
		.catch(() => school);
}

/* ---------- Child table row events (optional niceties) ---------- */

// When a user picks start/end AY in a course row, clear incompatible terms automatically
frappe.ui.form.on("Program Offering Course", {
	start_academic_year(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.start_term) {
			// If start_term's AY doesn't match anymore, clear it (server will also enforce)
			frappe.db.get_value("Term", row.start_term, "academic_year").then(r => {
				if (r && r.message && r.message.academic_year && r.message.academic_year !== row.start_academic_year) {
					frappe.model.set_value(cdt, cdn, "start_term", null);
				}
			});
		}
	},

	end_academic_year(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (row.end_term) {
			frappe.db.get_value("Term", row.end_term, "academic_year").then(r => {
				if (r && r.message && r.message.academic_year && r.message.academic_year !== row.end_academic_year) {
					frappe.model.set_value(cdt, cdn, "end_term", null);
				}
			});
		}
	}
});
