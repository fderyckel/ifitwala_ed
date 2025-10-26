// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/program/program.js

frappe.ui.form.on("Program", {
	onload(frm) {
		// Filter the child "course" link in the "courses" table
		frm.set_query("course", "courses", function (doc, cdt, cdn) {
			const picked = (doc.courses || [])
				.filter(r => r.course)
				.map(r => r.course);

			return {
				filters: [
					["Course", "name", "not in", picked],   // no duplicates
					["Course", "status", "=", "Active"]     // only Active
				]
			};
		});

		// Avoid picking the same Assessment Category twice in the grid
		frm.set_query("assessment_category", "assessment_categories", function (doc) {
			const chosen = (doc.assessment_categories || [])
				.map(r => (r.assessment_category || "").trim())
				.filter(Boolean);
			return {
				filters: [
					["Assessment Category", "name", "not in", chosen]
				]
			};
		});
	},

	onload_post_render(frm) {
		// keep your multiple add UX
		if (frm.get_field("courses")?.grid?.set_multiple_add) {
			frm.get_field("courses").grid.set_multiple_add("course");
		}

		// --- NEW: add the blue button on the Assessment Categories grid toolbar ---
		const grid = frm.fields_dict?.assessment_categories?.grid;
		if (grid && !frm.__inherit_btn_added) {
			const $btn = grid.add_custom_button(__("Inherit from Parent"), async () => {
				if (!frm.doc.parent_program) {
					frappe.msgprint({
						title: __("Missing Parent Program"),
						indicator: "red",
						message: __("Set a Parent Program first, then try again.")
					});
					return;
				}

				// Confirm overwrite if there are existing rows
				let ok_to_overwrite = true;
				if ((frm.doc.assessment_categories || []).length > 0) {
					ok_to_overwrite = await new Promise(resolve => {
						frappe.confirm(
							__("This will replace current Assessment Categories with the parent's list. Continue?"),
							() => resolve(true),
							() => resolve(false)
						);
					});
				}
				if (!ok_to_overwrite) return;

				frappe.call({
					method: "ifitwala_ed.curriculum.doctype.program.program.inherit_assessment_categories",
					freeze: true,
					args: {
						program: frm.doc.name,
						overwrite: 1
					},
					callback: () => {
						frm.reload_doc().then(() => {
							frm.refresh_field("assessment_categories");
							_update_remaining_weight_badge(frm);
							frappe.show_alert({
								indicator: "green",
								message: __("Imported categories from parent.")
							});
						});
					}
				});
			});

			// Make it primary blue (Bootstrap primary)
			$btn.addClass("btn-primary");
			frm.__inherit_btn_added = true;
		}

		// Live % helpers
		_bind_weight_handlers(frm);
		_update_remaining_weight_badge(frm);
	},

	before_save(frm) {
		// Lightweight client validation for scheme exclusivity and weight totals.
		_client_validate_assessment_scheme(frm);
		_client_validate_weights(frm);
	}
});


// to filter out courses that have already been picked out in the program.
frappe.ui.form.on("Program Course", {
	// (no change)
});


// -------------------------------------------------------------
// Helpers (client) — keep light; server remains source of truth
// -------------------------------------------------------------

function _bind_weight_handlers(frm) {
	const grid = frm.fields_dict?.assessment_categories?.grid;
	if (!grid || frm.__weight_handlers_bound) return;

	// React to value changes inside the child doctype
	frappe.ui.form.on("Program Assessment Category", {
		default_weight: function (frm, cdt, cdn) {
			const d = frappe.get_doc(cdt, cdn);
			// Clamp into [0, 100]
			let w = parseFloat(d.default_weight || 0);
			if (isNaN(w)) w = 0;
			if (w < 0) w = 0;
			if (w > 100) w = 100;
			if (w !== d.default_weight) {
				d.default_weight = w;
				refresh_field("assessment_categories");
			}
			_update_remaining_weight_badge(frm);
		},
		active: function (frm) {
			_update_remaining_weight_badge(frm);
		},
		assessment_category: function (frm) {
			_update_remaining_weight_badge(frm);
		}
	});

	// Also recompute when rows are added/removed
	const refreshBadge = () => _update_remaining_weight_badge(frm);
	grid.on_grid_after_delete = refreshBadge;
	grid.on_grid_after_add_row = refreshBadge;

	frm.__weight_handlers_bound = true;
}

function _update_remaining_weight_badge(frm) {
	const rows = frm.doc.assessment_categories || [];
	const total = rows
		.filter(r => cint(r.active) === 1)
		.reduce((acc, r) => acc + (parseFloat(r.default_weight) || 0), 0.0);

	const $wrap = $(frm.fields_dict.assessment_categories?.wrapper || null);
	if (!$wrap.length) return;

	let $badge = $wrap.find(".remaining-weight-badge");
	if ($badge.length === 0) {
		// Try to place it near grid header/footer
		const $target = $wrap.find(".grid-heading-row, .grid-footer").first();
		if ($target.length) {
			$badge = $(
				`<span class="badge bg-secondary remaining-weight-badge" style="margin-left:8px">${__("Active Total")} : <b>0.00</b>%</span>`
			);
			$target.append($badge);
		}
	}

	if ($badge && $badge.length) {
		$badge.find("b").text(total.toFixed(2));
		// quick visual hint when > 100
		$badge
			.removeClass("bg-secondary bg-danger bg-success")
			.addClass(total > 100.0001 ? "bg-danger" : (Math.abs(total - 100) < 0.0001 && cint(frm.doc.points) ? "bg-success" : "bg-secondary"));
	}
}

function _client_validate_assessment_scheme(frm) {
	const points = cint(frm.doc.points);
	const criteria = cint(frm.doc.criteria);
	const binary = cint(frm.doc.binary);

	const sum = points + criteria + binary;
	if (sum > 1) {
		frappe.throw(__("Select only one assessment scheme: either Points, or Criteria, or Binary."));
	}
	if (sum === 0) {
		frappe.throw(__("Select one assessment scheme for this Program (Points, Criteria, or Binary)."));
	}
}

function _client_validate_weights(frm) {
	const rows = frm.doc.assessment_categories || [];
	const points = cint(frm.doc.points);
	const binary = cint(frm.doc.binary);

	let activeTotal = 0.0;
	let hasActive = false;
	const over = [];
	const neg = [];
	const dupMap = new Set();
	const dups = [];

	for (const r of rows) {
		const cat = (r.assessment_category || "").trim();
		const w = parseFloat(r.default_weight || 0);
		const active = cint(r.active) === 1;

		// Duplicate guard
		if (cat) {
			if (dupMap.has(cat)) dups.push(`${r.idx}: ${cat}`);
			else dupMap.add(cat);
		}

		if (w < 0) neg.push(r.idx);
		if (w > 100) over.push(r.idx);
		if (active) {
			hasActive = true;
			activeTotal += (isNaN(w) ? 0 : w);
		}
	}

	if (dups.length) {
		frappe.throw(__("Duplicate Assessment Categories are not allowed:<br>{0}", [dups.join("<br>")]));
	}
	if (neg.length) {
		frappe.throw(__("Default Weight cannot be negative (rows: {0}).", [neg.join(", ")]));
	}
	if (over.length) {
		frappe.throw(__("Default Weight cannot exceed 100 (rows: {0}).", [over.join(", ")]));
	}

	if (points) {
		if (!hasActive) {
			frappe.throw(__("With Points selected, add at least one active Program Assessment Category."));
		}
		if (Math.abs(activeTotal - 100.0) > 0.0001) {
			frappe.throw(__("With Points selected, the total of active category weights must equal 100 (current total: {0}).", [activeTotal.toFixed(2)]));
		}
	} else {
		if (activeTotal > 100.0001) {
			frappe.throw(__("Total of active category weights must not exceed 100 (current total: {0}).", [activeTotal.toFixed(2)]));
		}
	}

	if (binary) {
		const nonZero = rows
			.filter(r => parseFloat(r.default_weight || 0) > 0.000001)
			.map(r => r.idx);
		if (nonZero.length) {
			frappe.throw(__("With Binary selected, category weights must all be 0 (rows: {0}).", [nonZero.join(", ")]));
		}
	}
}

function cint(v) {
	return (~~v) ? 1 : 0;
}
