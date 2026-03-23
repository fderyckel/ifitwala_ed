// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/program/program.js

frappe.ui.form.on("Program", {
	onload(frm) {
		frm.set_query("parent_program", () => ({
			query: "ifitwala_ed.curriculum.doctype.program.program.program_parent_query",
			filters: {
				current_program: frm.doc.name || null
			}
		}));

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

		frm.set_query("course", "course_basket_groups", function (doc) {
			const validCourses = (doc.courses || [])
				.filter(r => r.course)
				.map(r => r.course);

			if (!validCourses.length) {
				return {
					filters: [["Course", "name", "=", "___NONE___"]]
				};
			}

			return {
				filters: [["Course", "name", "in", validCourses]]
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
			_inject_program_button_style_once();
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

			$btn.removeClass((_, cls) => ((cls || "").match(/\bbtn[^\s]*/g) || []).join(" "));
			$btn.addClass("if-program-grid-action");
			frm.__inherit_btn_added = true;
		}

		// Live % helpers
		_bind_weight_handlers(frm);
		_update_remaining_weight_badge(frm);
		_refresh_effective_assessment_categories_hint(frm);
	},

	refresh: frappe.utils.debounce(async (frm) => {
		if (!frm.dashboard || !frm.dashboard.set_headline) return;

		const warnings = [];
		if (frm.doc.is_published && frm.doc.archive) {
			warnings.push(__("Program is archived and cannot be published."));
		}
		if (frm.doc.is_published && !frm.doc.program_slug) {
			warnings.push(__("Program slug is required to publish."));
		}

		if (frm.doc.is_published && !frm.doc.archive) {
			const profiles = await frappe.db.get_list("Program Website Profile", {
				filters: { program: frm.doc.name },
				fields: ["name", "status"],
				limit: 20
			});
			const publishedProfiles = (profiles || []).filter((row) => row.status === "Published");
			if (!profiles || profiles.length === 0) {
				warnings.push(__("Program is published but no Website Profile has been prepared yet."));
			} else if (publishedProfiles.length === 0) {
				warnings.push(__("Program website profiles are prepared, but none are published yet."));
			}
		}

		if (warnings.length) {
			const html = warnings.map((msg) => `• ${frappe.utils.escape_html(msg)}`).join("<br>");
			frm.dashboard.set_headline(`<span class="text-warning">${html}</span>`);
		} else {
			frm.dashboard.set_headline("");
		}

		_refresh_effective_assessment_categories_hint(frm);
		_toggle_make_parent_group_action(frm);
		_apply_root_program_guardrails(frm);
	}, 300),

	before_save(frm) {
		// ALLOW multiple schemes (points/binary/criteria/feedback)
		// Only guard weights if Points is ON.
		_client_validate_weights_when_points(frm);
	},

	parent_program(frm) {
		_handle_parent_program_change(frm);
	}
});


// to filter out courses that have already been picked out in the program.
frappe.ui.form.on("Program Course", {
	// (no change)
});


// -------------------------------------------------------------
// Helpers (client) — keep light; server remains source of truth
// -------------------------------------------------------------

function _inject_program_button_style_once() {
	const STYLE_ID = "if-program-grid-action-css";
	if (document.getElementById(STYLE_ID)) return;

	const style = document.createElement("style");
	style.id = STYLE_ID;
	style.textContent = `
		.if-program-grid-action{
			background: #1d4ed8;
			border: 1px solid #1d4ed8;
			color: #fff;
			border-radius: 0.5rem;
			padding: 0.32rem 0.72rem;
			font-size: 0.8rem;
			font-weight: 600;
		}
		.if-program-grid-action:hover,
		.if-program-grid-action:focus{
			background: #1e40af;
			border-color: #1e40af;
			color: #fff;
		}
		.if-program-weight-pill{
			padding: 0.18rem 0.55rem;
			border-radius: 999px;
			font-size: 0.78rem;
			font-weight: 600;
			line-height: 1.2;
			border: 1px solid transparent;
		}
		.if-program-weight-pill--neutral{
			background: #e2e8f0;
			border-color: #cbd5e1;
			color: #334155;
		}
		.if-program-weight-pill--danger{
			background: #fee2e2;
			border-color: #fecaca;
			color: #991b1b;
		}
		.if-program-weight-pill--success{
			background: #dcfce7;
			border-color: #bbf7d0;
			color: #166534;
		}
	`;
	document.head.appendChild(style);
}

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
		assessment_category: function (frm, cdt, cdn) {
			// Auto-pick color from master category if color_override is blank
			const d = frappe.get_doc(cdt, cdn);
			const cat = (d.assessment_category || "").trim();
			if (!cat) {
				_update_remaining_weight_badge(frm);
				return;
			}

			if (!d.color_override) {
				// Avoid .finally (not available on some builds)
				frappe.db.get_value("Assessment Category", cat, "assessment_category_color")
					.then(r => {
						const color = r && r.message && r.message.assessment_category_color;
						if (color) {
							d.color_override = color;
							refresh_field("assessment_categories");
						}
					})
					.catch(() => { /* ignore */ })
					.then(() => _update_remaining_weight_badge(frm));
			} else {
				_update_remaining_weight_badge(frm);
			}
		}
	});

	// Also recompute when rows are added/removed
	const refreshBadge = () => _update_remaining_weight_badge(frm);
	grid.on_grid_after_delete = refreshBadge;
	grid.on_grid_after_add_row = refreshBadge;

	frm.__weight_handlers_bound = true;
}

function _update_remaining_weight_badge(frm) {
	_inject_program_button_style_once();
	const rows = frm.doc.assessment_categories || [];
	const total = rows
		.filter(r => cint(r.active) === 1)
		.reduce((acc, r) => acc + (parseFloat(r.default_weight) || 0), 0.0);

	const $wrap = $(frm.fields_dict.assessment_categories?.wrapper || null);
	if (!$wrap.length) return;

	// 1) Clear any old badges we might have put in the wrong place
	$wrap.find(".remaining-weight-badge").remove();

	// 2) Prefer the toolbar right-side if available
	//    Frappe v16 grid structure usually has:
	//    .grid-toolbar
	//      ├─ .grid-buttons (left)
	//      └─ .grid-actions  (right)
	let host =
		$wrap.find(".grid-toolbar .grid-actions").first();  // right side
	if (!host.length) {
		// Fallback: append after buttons block (left)
		host = $wrap.find(".grid-toolbar .grid-buttons").first();
	}
	if (!host.length) {
		// Last fallback: grid footer
		host = $wrap.find(".grid-footer").first();
	}
	if (!host.length) {
		// Give up quietly if structure is unexpected
		return;
	}

	const $badge = $(
		`<span class="if-program-weight-pill if-program-weight-pill--neutral remaining-weight-badge"
				style="margin-left:8px; display:inline-flex; align-items:center; white-space:nowrap;">
				${__("Active Total")} : <b>${total.toFixed(2)}</b>%
			</span>`
	);
	host.append($badge);

	// Visual hint: if Points ON and total==100 → green; if >100 → red; else grey.
	const pointsOn = cint(frm.doc.points) === 1;
	$badge
		.removeClass("if-program-weight-pill--neutral if-program-weight-pill--danger if-program-weight-pill--success")
		.addClass(
			total > 100.0001
				? "if-program-weight-pill--danger"
				: pointsOn && Math.abs(total - 100) < 0.0001
					? "if-program-weight-pill--success"
					: "if-program-weight-pill--neutral"
		);
}

function _render_effective_assessment_categories_hint(frm, payload) {
	const $wrap = $(frm.fields_dict.assessment_categories?.wrapper || null);
	if (!$wrap.length) return;

	$wrap.find(".if-program-inherited-assessment-note").remove();

	if (!payload || !payload.inherited || !payload.source_program) {
		return;
	}

	const rows = Array.isArray(payload.rows) ? payload.rows : [];
	const categories = rows
		.map((row) => frappe.utils.escape_html(row.assessment_category || ""))
		.filter(Boolean)
		.join(", ");
	const sourceProgram = frappe.utils.escape_html(payload.source_program || "");

	const body = categories
		? __("Using inherited Assessment Categories from {0}: {1}", [sourceProgram, categories])
		: __("Using inherited Assessment Categories from {0}.", [sourceProgram]);

	$wrap.prepend(
		`<div class="if-program-inherited-assessment-note text-muted small" style="margin-bottom:8px;">
			${body}
		</div>`
	);
}

function _refresh_effective_assessment_categories_hint(frm) {
	const hasLocalRows = Array.isArray(frm.doc.assessment_categories) && frm.doc.assessment_categories.length > 0;
	const hasParent = !!(frm.doc.parent_program || "").trim();
	if (!frm.doc.name || !hasParent || hasLocalRows) {
		_render_effective_assessment_categories_hint(frm, null);
		return;
	}

	frappe.call({
		method: "ifitwala_ed.curriculum.doctype.program.program.get_effective_assessment_categories",
		args: { program: frm.doc.name },
		callback: (r) => _render_effective_assessment_categories_hint(frm, r.message || null),
	});
}

async function _handle_parent_program_change(frm) {
	const parentProgram = (frm.doc.parent_program || "").trim();
	if (!parentProgram) {
		frm.remove_custom_button(__("Make Parent a Group"), __("Actions"));
		return;
	}

	const parentRow = await _get_program_row(parentProgram);
	if (!parentRow || cint(parentRow.is_group) === 1) {
		_toggle_make_parent_group_action(frm);
		return;
	}

	const parentLabel = parentRow.program_name || parentProgram;
	const shouldPromote = await new Promise(resolve => {
		frappe.confirm(
			__(
				"Parent Program {0} is not marked as Group. Convert it to a Group now so it can own child programs?",
				[parentLabel]
			),
			() => resolve(true),
			() => resolve(false)
		);
	});

	if (!shouldPromote) {
		frm.set_value("parent_program", "");
		frappe.msgprint({
			title: __("Parent Program Cleared"),
			message: __("Only Group Programs can be used as Parent Program."),
			indicator: "orange"
		});
		return;
	}

	await _promote_program_to_group(frm, parentProgram, parentLabel);
}

async function _toggle_make_parent_group_action(frm) {
	frm.remove_custom_button(__("Make Parent a Group"), __("Actions"));

	const parentProgram = (frm.doc.parent_program || "").trim();
	if (!parentProgram) return;

	const parentRow = await _get_program_row(parentProgram);
	if (!parentRow || cint(parentRow.is_group) === 1) return;

	const parentLabel = parentRow.program_name || parentProgram;
	const $button = frm.add_custom_button(__("Make Parent a Group"), async () => {
		await _promote_program_to_group(frm, parentProgram, parentLabel);
	}, __("Actions"));
	$button.addClass("btn-primary");
}

async function _promote_program_to_group(frm, program, label) {
	const response = await frappe.call({
		method: "ifitwala_ed.curriculum.doctype.program.program.make_program_group",
		args: { program },
		freeze: true,
		freeze_message: __("Updating Parent Program...")
	});

	if (response?.message?.changed) {
		frappe.show_alert({
			indicator: "green",
			message: __("{0} is now marked as Group.", [label])
		});
	}

	await _toggle_make_parent_group_action(frm);
}

async function _get_program_row(program) {
	if (!program) return null;
	const response = await frappe.db.get_value("Program", program, ["program_name", "is_group"]);
	return response?.message || null;
}

function _apply_root_program_guardrails(frm) {
	const isRootProgram = (frm.doc.name || "") === "All Programs";
	frm.set_df_property("parent_program", "read_only", isRootProgram ? 1 : 0);
	frm.set_df_property("archive", "read_only", isRootProgram ? 1 : 0);
	frm.set_df_property("is_group", "read_only", isRootProgram ? 1 : 0);
}

// NEW: with multi-scheme, only enforce weight rules if Points is enabled.
function _client_validate_weights_when_points(frm) {
	if (cint(frm.doc.points) !== 1) return; // nothing to enforce

	const rows = frm.doc.assessment_categories || [];
	let activeTotal = 0.0;
	let hasActive = false;
	const over = [];
	const neg = [];
	const dups = [];
	const seen = new Set();

	for (const r of rows) {
		const cat = (r.assessment_category || "").trim();
		const w = parseFloat(r.default_weight || 0);
		const active = cint(r.active) === 1;

		// Duplicate guard (still makes sense globally)
		if (cat) {
			if (seen.has(cat)) dups.push(`${r.idx}: ${cat}`);
			else seen.add(cat);
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

	// For Points, we require active rows and total ≤ 100 (exact 100 optional; you can harden later on publish)
	if (!hasActive) {
		frappe.throw(__("With Points enabled, add at least one active Assessment Category with a weight."));
	}
	if (activeTotal > 100.0001) {
		frappe.throw(__("For Points, the total of active category weights must not exceed 100 (current total: {0}).", [activeTotal.toFixed(2)]));
	}
}

function cint(v) {
	return (~~v) ? 1 : 0;
}
