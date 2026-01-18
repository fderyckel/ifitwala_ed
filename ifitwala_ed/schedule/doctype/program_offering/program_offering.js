// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/program_offering/program_offering.js


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

function bind_offering_year_query(frm) {
	// Fields dict for the multi-select table
	const table_field = frm.fields_dict.offering_academic_years;
	if (!table_field || !table_field.grid) {
		// grid not ready yet, try again shortly
		setTimeout(() => bind_offering_year_query(frm), 200);
		return;
	}

	const grid = table_field.grid;
	const col = grid.get_field("academic_year");
	if (col) {
		col.get_query = () => ({
			query: "ifitwala_ed.schedule.doctype.program_offering.program_offering.academic_year_link_query",
			filters: { school: frm.doc.school || null }
		});
	}

	if (!grid.__ay_bound) {
		grid.on("grid-rows-rendered", () => {
			const c = grid.get_field("academic_year");
			if (c) {
				c.get_query = () => ({
					query: "ifitwala_ed.schedule.doctype.program_offering.program_offering.academic_year_link_query",
					filters: { school: frm.doc.school || null }
				});
			}
		});
		grid.__ay_bound = true;
	}
}


/* ---------- Catalog dialog rendering + helpers ---------- */

// Build the list UI inside the dialog
function render_catalog_list($list, rows) {
  // Inject a scoped style once (beats Bootstrap 4/5; no global leak)
  if (!document.getElementById("po-required-pill-style")) {
    const style = document.createElement("style");
    style.id = "po-required-pill-style";
    style.textContent = `
      .po-catalog-dialog .po-required-badge{
        background: #FDE68A !important;  /* pale orange */
        color: #92400E !important;        /* readable on pale orange */
        font-weight: 600;
        font-size: 0.95rem;               /* larger text */
        padding: 0.30rem 0.70rem;         /* bigger pill */
        border-radius: 9999px;            /* fully rounded */
        line-height: 1;
        vertical-align: middle;
      }
    `;
    document.head.appendChild(style);
  }

  $list.empty();

  (rows || []).forEach((r) => {
    const course = frappe.utils.escape_html(r.course);
    const cname  = frappe.utils.escape_html(r.course_name || r.course);
    const req    = r.required ? 1 : 0;

    const $row = $(`
      <label class="list-group-item d-flex align-items-start gap-2">
        <input
          type="checkbox"
          class="pc-pick form-check-input mt-1"
          data-course="${course}"
          data-course_name="${cname}"
          data-required="${req}"
        >
        <div class="flex-grow-1">
          <div class="fw-semibold">${cname}</div>
          <div class="text-muted small">${course}</div>
        </div>
        <div class="ms-auto">
          ${req ? `<span class="badge badge-pill po-required-badge">Required</span>` : ""}
        </div>
      </label>
    `);
    $list.append($row);
  });
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

	d.$wrapper.addClass("po-catalog-dialog");

	const $list = $('<div class="list-group" style="max-height:50vh;overflow:auto;"></div>');
	d.get_field("list_html").$wrapper.empty().append($list);

	// initial load (already excludes added)
	fetch_catalog_rows(frm, "", rows => render_catalog_list($list, rows));

	d.show();
}

/* ---------------- Non-catalog Picker ---------------- */

// Fetch Course docs not already in this offering, only "Active" status
function fetch_non_catalog_rows(frm, search, on_done) {
	const exclude = current_offering_course_names(frm); // already-added on this offering
	const term = (search || "").trim();

	const args = {
		doctype: "Course",
		fields: ["name", "course_name", "status"],
		limit_page_length: 50,
		order_by: "modified desc",
		// Only active courses (per your Course schema: Status = Active/Discontinued)
		filters: [["Course", "status", "=", "Active"]],
	};

	// Exclude already-added courses on this offering
	if (exclude && exclude.length) {
		args.filters.push(["Course", "name", "not in", exclude]);
	}

	// Optional search across name + course_name
	if (term) {
		args.or_filters = [
			["Course", "name", "like", `%${term}%`],
			["Course", "course_name", "like", `%${term}%`],
		];
	}

	frappe.call({ method: "frappe.client.get_list", args })
		.then((r) => {
			const raw = r.message || [];
			const rows = raw.map((x) => ({
				course: x.name,
				course_name: x.course_name || x.name,
				required: 0,
				non_catalog: 1,
			}));
			on_done(rows);
		})
		.catch(() => {
			on_done([]);
			frappe.show_alert({ message: __("Could not load non-catalog courses."), indicator: "orange" });
		});
}

// Custom dialog modeled exactly after the Catalog picker
function open_non_catalog_picker(frm) {
	// 1) validate AY envelope and grab start/end
	if (!require_ay_span(frm)) return;
	const { startAY, endAY } = get_ay_bounds(frm);
	if (!startAY || !endAY) {
		frappe.msgprint({ message: __("Add at least one Academic Year to the Offering first."), indicator: "orange" });
		return;
	}

	// 2) build dialog
	const d = new frappe.ui.Dialog({
		title: __("Add Non-catalog Courses"),
		size: "extra-large",
		primary_action_label: __("Add Selected"),
		primary_action: () => {
			const chosen = get_checked_rows($list);
			if (!chosen.length) return d.hide();

			let added = 0;
			for (const r of chosen) {
				// mark non-catalog and set AY span
				const ok = add_offering_course_if_new(frm, {
					course: r.course,
					course_name: r.course_name || r.course,
					required: 0,
					non_catalog: 1,
					catalog_ref: null,
					start_academic_year: startAY,
					end_academic_year: endAY,
				});
				if (ok) added++;
			}
			if (added) {
				frm.refresh_field("offering_courses");
				const term = (d.get_value("search") || "").trim();
				// refresh list to hide just-added
				fetch_non_catalog_rows(frm, term, (rows) => render_catalog_list($list, rows));
			}
		},
		fields: [
			{
				fieldname: "search",
				fieldtype: "Data",
				label: __("Search courses..."),
				change: () => {
					const term = (d.get_value("search") || "").trim();
					fetch_non_catalog_rows(frm, term, (rows) => render_catalog_list($list, rows));
				},
			},
			{ fieldname: "list_html", fieldtype: "HTML" },
		],
	});

	d.$wrapper.addClass("po-catalog-dialog");

	// 3) mount list + initial fetch (excludes already-added)
	const $list = $('<div class="list-group" style="max-height:50vh;overflow:auto;"></div>');
	d.get_field("list_html").$wrapper.empty().append($list);
	fetch_non_catalog_rows(frm, "", (rows) => render_catalog_list($list, rows));

	d.show();
}

/* ---------------- Manual Draft Tuition Invoice ---------------- */

function build_invoice_row($list, rowIndex) {
	const rowId = `line_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
	const $row = $(`
		<div class="border rounded p-2 mb-2">
			<div class="d-flex justify-content-between align-items-center mb-2">
				<div class="fw-semibold">Line ${rowIndex}</div>
			</div>
			<div class="row g-2"></div>
		</div>
	`);

	const $header = $row.find(".d-flex").first();
	const $remove = $(`<button class="btn btn-sm btn-link text-danger">${__("Remove")}</button>`);
	$header.append($remove);

	const $fields = $row.find(".row").first();

	function add_field(df, colClass) {
		const $col = $(`<div class="${colClass}"></div>`);
		$fields.append($col);
		const control = frappe.ui.form.make_control({
			df: {
				...df,
				fieldname: `${df.fieldname}_${rowId}`,
			},
			parent: $col,
			render_input: true,
		});
		control.refresh();
		if (df.default !== undefined) {
			control.set_value(df.default);
		}
		return control;
	}

	const controls = {
		billable_offering: add_field(
			{
				fieldname: "billable_offering",
				fieldtype: "Link",
				options: "Billable Offering",
				label: __("Billable Offering"),
				reqd: 1,
			},
			"col-md-6"
		),
		student: add_field(
			{
				fieldname: "student",
				fieldtype: "Link",
				options: "Student",
				label: __("Student"),
			},
			"col-md-6"
		),
		qty: add_field(
			{
				fieldname: "qty",
				fieldtype: "Float",
				label: __("Qty"),
				reqd: 1,
				default: 1,
			},
			"col-md-2"
		),
		rate: add_field(
			{
				fieldname: "rate",
				fieldtype: "Currency",
				label: __("Rate"),
				reqd: 1,
			},
			"col-md-3"
		),
		charge_source: add_field(
			{
				fieldname: "charge_source",
				fieldtype: "Select",
				label: __("Charge Source"),
				options: "Program Offering\nExtra\nManual",
				default: "Program Offering",
			},
			"col-md-3"
		),
		description: add_field(
			{
				fieldname: "description",
				fieldtype: "Data",
				label: __("Description"),
			},
			"col-md-4"
		),
	};

	$remove.on("click", () => {
		$row.remove();
	});

	$list.append($row);
	return { $row, controls };
}

function open_tuition_invoice_dialog(frm) {
	if (frm.is_new() || frm.is_dirty()) {
		frappe.msgprint({ message: __("Please save the Program Offering before creating an invoice."), indicator: "orange" });
		return;
	}

	const d = new frappe.ui.Dialog({
		title: __("Create Draft Tuition Invoice"),
		fields: [
			{
				fieldname: "account_holder",
				fieldtype: "Link",
				label: __("Account Holder"),
				options: "Account Holder",
				reqd: 1,
			},
			{
				fieldname: "posting_date",
				fieldtype: "Date",
				label: __("Posting Date"),
				reqd: 1,
				default: frappe.datetime.get_today(),
			},
			{ fieldname: "items_html", fieldtype: "HTML" },
		],
		primary_action_label: __("Create Draft Invoice"),
		primary_action(values) {
			if (!values) {
				return;
			}

			const rows = [];
			d.$wrapper.find(".po-invoice-line").each(function () {
				const rowData = $(this).data("rowData");
				if (rowData) rows.push(rowData);
			});

			if (!rows.length) {
				frappe.msgprint({ message: __("At least one line item is required."), indicator: "red" });
				return;
			}

			const payload = [];
			for (let i = 0; i < rows.length; i += 1) {
				const row = rows[i];
				const billable_offering = row.controls.billable_offering.get_value();
				const qty = parseFloat(row.controls.qty.get_value() || 0);
				const rate_raw = row.controls.rate.get_value();
				const rate = rate_raw === "" || rate_raw === null ? null : parseFloat(rate_raw);
				const description = row.controls.description.get_value();
				const student = row.controls.student.get_value();
				const charge_source = row.controls.charge_source.get_value() || "Program Offering";

				if (!billable_offering) {
				frappe.msgprint({ message: __("Row {0}: Billable Offering is required.", [i + 1]), indicator: "red" });
				return;
			}
			if (!qty || qty <= 0) {
				frappe.msgprint({ message: __("Row {0}: Qty must be greater than zero.", [i + 1]), indicator: "red" });
				return;
			}
			if (rate === null || Number.isNaN(rate)) {
				frappe.msgprint({ message: __("Row {0}: Rate is required.", [i + 1]), indicator: "red" });
				return;
			}
			if (rate < 0) {
				frappe.msgprint({ message: __("Row {0}: Rate cannot be negative.", [i + 1]), indicator: "red" });
				return;
			}
			if (rate === 0 && !description) {
				frappe.msgprint({ message: __("Row {0}: Description is required for zero-rate lines.", [i + 1]), indicator: "red" });
				return;
			}

				payload.push({
					billable_offering,
					qty,
					rate,
					student,
					description,
					charge_source,
				});
			}

			frappe.call({
				method: "ifitwala_ed.schedule.doctype.program_offering.program_offering.create_draft_tuition_invoice",
				args: {
					program_offering: frm.doc.name,
					account_holder: values.account_holder,
					posting_date: values.posting_date,
					items: JSON.stringify(payload),
				},
				callback: (r) => {
					const invoice = r && r.message && r.message.sales_invoice;
					if (invoice) {
						frappe.set_route("Form", "Sales Invoice", invoice);
					}
					d.hide();
				},
			});
		},
	});

	const $itemsWrapper = d.get_field("items_html").$wrapper;
	$itemsWrapper.empty();

	const $toolbar = $(`
		<div class="d-flex justify-content-between align-items-center mb-2">
			<div class="text-muted small">${__("Add one or more line items.")}</div>
		</div>
	`);
	const $addBtn = $(`<button class="btn btn-sm btn-secondary">${__("Add Line")}</button>`);
	$toolbar.append($addBtn);
	$itemsWrapper.append($toolbar);

	const $list = $('<div class="po-invoice-lines"></div>');
	$itemsWrapper.append($list);

	function add_row() {
		const rowIndex = $list.find(".po-invoice-line").length + 1;
		const rowData = build_invoice_row($list, rowIndex);
		rowData.$row.addClass("po-invoice-line");
		rowData.$row.data("rowData", rowData);
	}

	$addBtn.on("click", () => add_row());

	add_row();
	d.show();
}



frappe.ui.form.on("Program Offering", {

	onload(frm) {
		bind_offering_year_query(frm);
		frm.set_query('school', () => {
			return {
				query: 'ifitwala_ed.utilities.school_tree.get_descendant_schools',
				filters: { user_school: frappe.defaults.get_default('school') }
			};
		});
	},

	refresh(frm) {
		// remove any leftover custom buttons to avoid duplicates
		if (frm.clear_custom_buttons) frm.clear_custom_buttons();

		bind_offering_year_query(frm);

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

		const createInvoice = frm.add_custom_button(__("Create Draft Tuition Invoice"), () => open_tuition_invoice_dialog(frm));
		if (createInvoice) {
			createInvoice.removeClass("btn-default btn-secondary").addClass("btn-outline-secondary");
			createInvoice.addClass("ms-2");
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
