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


/* ---------------- Helpers: AY defaults for new rows ---------------- */

function get_ay_bounds(frm) {
	const ays = (frm.doc.offering_academic_years || []).map(r => r.academic_year).filter(Boolean);
	if (!ays.length) return { startAY: null, endAY: null };
	return { startAY: ays[0], endAY: ays[ays.length - 1] }; // assume user ordered; server also enforces overlap/order
}


/* ---------- Catalog dialog rendering + helpers ---------- */

// Build the list UI inside the dialog
function render_catalog_list($list, rows) {
  $list.empty();

  const items = Array.isArray(rows) ? rows : [];
  if (!items.length) {
    $list.append(
      `<div class="text-muted p-3">${__("No matching courses in catalog.")}</div>`
    );
    return;
  }

  for (const r of items) {
    const course = frappe.utils.escape_html(r.course || "");
    const cname  = frappe.utils.escape_html(r.course_name || r.course || "");
    const req    = r.required ? 1 : 0;

    const $row = $(`
      <div class="list-group-item">
        <div class="d-flex align-items-start gap-2">
          <input type="checkbox" class="form-check-input mt-1 pc-pick"
                 data-course="${course}"
                 data-course_name="${cname}"
                 data-required="${req}">
          <div class="flex-grow-1">
            <div class="fw-semibold">${cname}</div>
            <div class="text-muted small">${course}</div>
          </div>
          ${req ? `<span class="badge bg-secondary">${__("Required")}</span>` : ""}
        </div>
      </div>
    `);
    $list.append($row);
  }
}

// Read checked rows from the dialog list
function get_checked_rows($list) {
  const picked = [];
  $list.find('input.pc-pick:checked').each(function () {
    const $cb = $(this);
    picked.push({
      course: $cb.data("course"),
      course_name: $cb.data("course_name"),
      required: $cb.data("required") ? 1 : 0,
    });
  });
  return picked;
}

// Safe add (skip if already present). Returns true if added.
function add_offering_course_if_new(frm, payload) {
  const existing = new Set((frm.doc.offering_courses || [])
    .map(r => r.course)
    .filter(Boolean));

  if (payload.course && existing.has(payload.course)) {
    return false; // already in child table
  }

  const row = frm.add_child("offering_courses");
  row.course = payload.course || null;
  row.course_name = payload.course_name || payload.course || null;
  row.required = payload.required ? 1 : 0;
  row.elective_group = payload.elective_group || "";
  row.non_catalog = payload.non_catalog ? 1 : 0;
  row.catalog_ref = payload.catalog_ref || null;

  // If caller provided AY span, keep it; else leave empty
  if (payload.start_academic_year) row.start_academic_year = payload.start_academic_year;
  if (payload.end_academic_year)   row.end_academic_year   = payload.end_academic_year;

  return true;
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
	// 1) validate
	if (!require_ay_span(frm)) return;

	// 2) read the envelope safely
	const { startAY, endAY } = get_ay_bounds(frm);
	if (!startAY || !endAY) {
		frappe.msgprint({ message: __("Add at least one Academic Year to the Offering first."), indicator: "orange" });
		return;
	}

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
					start_academic_year: startAY,
					end_academic_year:   endAY,
				});
				if (ok) added++;
			}
			if (added) {
				frm.refresh_field("offering_courses");
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

	// initial load (already excludes added)
	fetch_catalog_rows(frm, "", rows => render_catalog_list($list, rows));

	d.show();
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

		// Prevent Object.keys(null) inside MultiSelectDialog.get_primary_filters:
		primary_filters: {},
		add_filters_group: 1,

		// keep it lean: only active courses
		get_query: () => ({ filters: { disabled: 0 } }),
		primary_action_label: __("Add Selected"),
		action(selections) {
			const picked = Array.isArray(selections) ? selections : [];
			const seen = new Set((frm.doc.offering_courses || []).map(r => r.course).filter(Boolean));
			let added = 0;

			for (const name of picked) {
				if (seen.has(name)) {
					frappe.show_alert({ message: __("Skipped duplicate: {0}", [name]), indicator: "orange" });
					continue;
				}
				const row = frm.add_child("offering_courses");
				row.course = name;
				row.course_name = name;
				row.required = 0;
				row.non_catalog = 1;
				row.catalog_ref = null;
				row.start_academic_year = startAY;
				row.end_academic_year = endAY;
				seen.add(name);
				added++;
			}

			if (added) frm.refresh_field("offering_courses");
			this.dialog.hide();
			frappe.show_alert({ message: __("Added {0} non-catalog course(s).", [added]), indicator: "green" });
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

frappe.ui.form.on("Program Offering Course", {
	course(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row) {
			const { startAY, endAY } = get_ay_bounds(frm);
			if (startAY && !row.start_academic_year) row.start_academic_year = startAY;
			if (endAY && !row.end_academic_year)     row.end_academic_year   = endAY;
			frm.refresh_field("offering_courses");
		}
	},
});