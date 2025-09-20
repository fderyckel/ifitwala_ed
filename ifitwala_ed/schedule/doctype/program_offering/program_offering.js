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

function open_catalog_picker(frm) {
	if (!frm.doc.program) {
		frappe.msgprint({ message: __("Pick a Program first."), indicator: "orange" });
		return;
	}

	const dlg = new frappe.ui.Dialog({
		title: __("Add Courses from Catalog"),
		size: "large",
		primary_action_label: __("Add Selected"),
		primary_action: () => {
			const chosen = get_checked_rows();
			add_catalog_rows(frm, chosen);
			dlg.hide();
		},
		secondary_action_label: __("Close"),
		secondary_action: () => dlg.hide()
	});

	dlg.$body.append(`
		<div class="mb-3">
			<input type="text" class="form-control po-catalog-search" placeholder="${__("Search courses…")}">
		</div>
		<div class="po-catalog-list list-group" style="max-height: 420px; overflow: auto;"></div>
	`);

	const $search = dlg.$body.find(".po-catalog-search");
	const $list   = dlg.$body.find(".po-catalog-list");

	let lastQuery = "";
	let inflight  = 0;

	const fetch_and_render = (q="") => {
		inflight++;
		frappe.call({
			method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.program_course_options",
			args: { program: frm.doc.program, search: q, start: 0, limit: 400 },
		}).then(r => {
			inflight--;
			const rows = r.message || [];
			render_catalog_list($list, rows);
		}).catch(() => { inflight--; });
	};

	const debounced = frappe.utils.debounce(() => {
		const q = ($search.val() || "").trim();
		if (q === lastQuery && !inflight) return;
		lastQuery = q;
		fetch_and_render(q);
	}, 250);

	$search.on("input", debounced);

	// initial load
	fetch_and_render("");

	dlg.show();

	function render_catalog_list($container, rows) {
		$container.empty();
		if (!rows.length) {
			$container.append(`<div class="text-muted p-3">${__("No results")}.</div>`);
			return;
		}
		for (const r of rows) {
			const id = frappe.utils.get_random(8);
			const reqBadge = r.required ? `<span class="badge bg-primary ms-2">${__("Required")}</span>` : "";
			$container.append(`
				<label class="list-group-item d-flex align-items-center gap-3">
					<input class="form-check-input po-pick" type="checkbox" data-row='${frappe.utils.escape_html(JSON.stringify(r))}'>
					<div>
						<div class="fw-semibold">${frappe.utils.escape_html(r.course_name || r.course || "")}${reqBadge}</div>
						<div class="text-muted small">${frappe.utils.escape_html(r.course || "")}</div>
					</div>
				</label>
			`);
		}
	}

	function get_checked_rows() {
		const out = [];
		$list.find(".po-pick:checked").each((_, el) => {
			try {
				out.push(JSON.parse($(el).attr("data-row")));
			} catch (e) { /* ignore */ }
		});
		return out;
	}
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
		// clear any previously added custom buttons to avoid duplicates on refresh
		if (frm.clear_custom_buttons) frm.clear_custom_buttons();

		// PRIMARY (blue): Add from Catalog
		frm.page.set_primary_action(__("Add from Catalog"), () => open_catalog_picker(frm));

		// SECOND button (separate, not nested)
		const nonCatBtn = frm.add_custom_button(__("Add Non-catalog"), () => open_non_catalog_picker(frm));
		// make it visibly blue-ish even on themes that override defaults
		if (nonCatBtn) {
			nonCatBtn.removeClass("btn-default");
			nonCatBtn.addClass("btn-outline-primary");
			nonCatBtn.addClass("ms-2"); // small spacing
		}

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
