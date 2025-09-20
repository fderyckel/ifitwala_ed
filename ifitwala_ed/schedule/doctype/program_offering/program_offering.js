// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

function apply_server_defaults_if_empty(frm) {
	if (!frm.doc.program || !frm.doc.school) return;

	const ayNames = (frm.doc.offering_academic_years || [])
		.map(r => r.academic_year)
		.filter(Boolean);

	if (!ayNames.length) return;

	frappe.call({
		method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.compute_program_offering_defaults",
		args: {
			program: frm.doc.program,
			school: frm.doc.school,
			ay_names: JSON.stringify(ayNames)
		},
		callback: (r) => {
			const out = (r && r.message) || {};
			if (!frm.doc.start_date && out.start_date) frm.set_value("start_date", out.start_date);
			if (!frm.doc.end_date && out.end_date) frm.set_value("end_date", out.end_date);
			if (!frm.doc.offering_title && out.offering_title) frm.set_value("offering_title", out.offering_title);
		}
	});
}

/* ---------------- Header Buttons (blue, not nested) ---------------- */

function ensure_header_buttons(frm) {
	if (frm._po_buttons_done) return;

	// Add From Catalog
	const b1 = frm.page.add_inner_button(__("Add From Catalog"), () => open_catalog_picker(frm));
	b1.addClass("btn-primary"); // blue

	// Add Non-catalog
	const b2 = frm.page.add_inner_button(__("Add Non-catalog"), () => open_non_catalog_picker(frm));
	b2.addClass("btn-primary"); // blue

	frm._po_buttons_done = true;
}

/* ---------------- Helpers: AY defaults for new rows ---------------- */

function get_ay_bounds(frm) {
	const ays = (frm.doc.offering_academic_years || []).map(r => r.academic_year).filter(Boolean);
	if (!ays.length) return { startAY: null, endAY: null };
	return { startAY: ays[0], endAY: ays[ays.length - 1] }; // assume user ordered; server also enforces overlap/order
}

/* ---------------- Helpers for default span ---------------- */
function first_and_last_ay(frm) {
	const ays = (frm.doc.offering_academic_years || []).map(r => r.academic_year).filter(Boolean);
	return { first: ays.length ? ays[0] : null, last: ays.length ? ays[ays.length - 1] : null };
}

function insert_offering_course_rows(frm, rows) {
	const span = first_and_last_ay(frm);
	(rows || []).forEach(r => {
		const child = frm.add_child("offering_courses");
		child.course = r.course;
		child.course_name = r.course_name || r.course;
		child.required = r.required ? 1 : 0;
		child.elective_group = r.elective_group || "";
		if ("non_catalog" in r) child.non_catalog = r.non_catalog ? 1 : 0;
		if ("exception_reason" in r) child.exception_reason = r.exception_reason || "";
		if ("catalog_ref" in r) child.catalog_ref = r.catalog_ref || "";

		// Default full span to offering AY envelope
		if (span.first) child.start_academic_year = span.first;
		if (span.last)  child.end_academic_year = span.last;
	});
	frm.refresh_field("offering_courses");
}

/* ---------------- Catalog Picker ---------------- */

function get_selected_ay_names(frm) {
	return (frm.doc.offering_academic_years || [])
		.map(r => r.academic_year)
		.filter(Boolean);
}

function require_ay_span(frm) {
	if (!frm.doc.program) {
		frappe.msgprint({ message: __("Please select a Program first."), indicator: "orange" });
		return false;
	}
	const ays = get_selected_ay_names(frm);
	if (!ays.length) {
		frappe.msgprint({ message: __("Please add at least one Academic Year before adding courses."), indicator: "orange" });
		return false;
	}
	return true;
}

function current_offering_course_names(frm) {
	return (frm.doc.offering_courses || [])
		.map(r => r.course)
		.filter(Boolean);
}

function fetch_catalog_rows(frm, search, on_done) {
	const exclude = current_offering_course_names(frm);

	frappe.call({
		method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.program_course_options",
		args: {
			program: frm.doc.program,
			search: search || "",
			exclude_courses: exclude,   // << new
		}
	}).then(r => on_done(r.message || []));
}

function open_catalog_picker(frm) {
	const span = require_ay_span(frm);
	if (!span) return;

	const d = new frappe.ui.Dialog({
		title: __("Add Courses from Catalog"),
		size: "extra-large",
		primary_action_label: __("Add Selected"),
		primary_action: () => {
			const chosen = get_checked_rows($list);
			if (!chosen.length) return d.hide();

			let added = 0;
			for (const r of chosen) {
				const ok = add_offering_course_if_new(frm, {
					course: r.course,
					course_name: r.course_name || r.course,
					required: !!r.required,
					non_catalog: 0,
					catalog_ref: `${frm.doc.program}::${r.course}`,
					start_academic_year: span.startAY,
					end_academic_year:   span.endAY,
				});
				if (ok) added++;
			}
			if (added) {
				frm.refresh_field("offering_courses");

				// after adding, refresh the dialog list so those disappear
				const term = (d.get_value("search") || "").trim();
				fetch_catalog_rows(frm, term, rows => render_catalog_list($list, rows));
			}
		},
		fields: [
			{
				fieldname: "search",
				fieldtype: "Data",
				label: __("Search courses..."),
				change: () => {
					const term = (d.get_value("search") || "").trim();
					fetch_catalog_rows(frm, term, rows => render_catalog_list($list, rows));
				}
			},
			{ fieldname: "list_html", fieldtype: "HTML" }
		]
	});

	const $list = $('<div class="list-group" style="max-height:50vh;overflow:auto;"></div>');
	d.get_field("list_html").$wrapper.empty().append($list);

	// initial fetch (excludes already-added)
	fetch_catalog_rows(frm, "", rows => render_catalog_list($list, rows));

	d.show();
}


function add_catalog_rows(frm, picked) {
	if (!picked || !picked.length) return;

	const { startAY, endAY } = get_ay_bounds(frm);
	if (!startAY || !endAY) {
		frappe.msgprint({ message: __("Add at least one Academic Year to the Offering first."), indicator: "orange" });
		return;
	}

	const seen = new Set((frm.doc.offering_courses || []).map(r => r.course).filter(Boolean));

	for (const r of picked) {
		// Avoid duplicates by Course on the offering
		if (r.course && seen.has(r.course)) continue;
		const row = frm.add_child("offering_courses");
		row.course = r.course || null;
		row.course_name = r.course_name || r.course || null;
		row.required = r.required ? 1 : 0;
		row.non_catalog = 0;
		row.catalog_ref = `${frm.doc.program}::${r.course || r.course_name || ""}`;
		row.start_academic_year = startAY;
		row.end_academic_year = endAY;
		seen.add(r.course);
	}

	frm.refresh_field("offering_courses");
	frappe.show_alert({ message: __("Added {0} course(s) from catalog.", [picked.length]), indicator: "green" });
}

/* ---------------- Non-catalog Picker ---------------- */


function open_non_catalog_picker(frm) {
	const { startAY, endAY } = get_ay_bounds(frm);
	if (!startAY || !endAY) {
		frappe.msgprint({ message: __("Add at least one Academic Year to the Offering first."), indicator: "orange" });
		return;
	}

	new frappe.ui.form.MultiSelectDialog({
		doctype: "Course",
		size: "large",
		pagelength: 20,
		// optional: filter to active courses
		get_query: () => ({ filters: { disabled: 0 } }),
		primary_action_label: __("Add Selected"),
		action(selections) {
			const seen = new Set((frm.doc.offering_courses || []).map(r => r.course).filter(Boolean));
			for (const name of selections) {
				if (seen.has(name)) continue;
				const row = frm.add_child("offering_courses");
				row.course = name;
				row.course_name = name;
				row.required = 0;
				row.non_catalog = 1;
				row.catalog_ref = null;
				row.start_academic_year = startAY;
				row.end_academic_year = endAY;
				seen.add(name);
			}
			frm.refresh_field("offering_courses");
			this.dialog.hide();
			frappe.show_alert({ message: __("Added {0} non-catalog course(s).", [selections.length]), indicator: "green" });
		},
	});
}

frappe.ui.form.on("Program Offering", {
	refresh(frm) {
		// remove any leftover custom buttons to avoid duplicates
		if (frm.clear_custom_buttons) frm.clear_custom_buttons();

		// Add from Catalog (blue, standalone on the left)
		const addFrom = frm.add_custom_button(__("Add from Catalog"), () => open_catalog_picker(frm));
		if (addFrom) {
			addFrom.removeClass("btn-default btn-secondary").addClass("btn-primary");
		}

		// Add Non-catalog (outlined blue, standalone on the left)
		const addNonCat = frm.add_custom_button(__("Add Non-catalog"), () => open_non_catalog_picker(frm));
		if (addNonCat) {
			addNonCat.removeClass("btn-default btn-secondary").addClass("btn-outline-primary");
			addNonCat.addClass("ms-2"); // small spacing
		}

		// DO NOT call set_primary_action here; it forces a right-side black button
		apply_server_defaults_if_empty(frm);
	},

	program(frm) {
		apply_server_defaults_if_empty(frm);
	},
	
	school(frm) {
		apply_server_defaults_if_empty(frm);
	}
});

frappe.ui.form.on("Program Offering Academic Year", {
	academic_year(frm) {
		apply_server_defaults_if_empty(frm);
	}
});
