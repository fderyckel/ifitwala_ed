// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

const CATEGORY_METHODS = new Set(["Weighted Categories", "Category + Task Weight Hybrid"]);

frappe.ui.form.on("Assessment Scheme", {
	refresh(frm) {
		update_category_visibility(frm);
		update_weight_intro(frm);
	},
	calculation_method(frm) {
		update_category_visibility(frm);
		update_weight_intro(frm);
	},
	categories_add(frm) {
		update_weight_intro(frm);
	},
	categories_remove(frm) {
		update_weight_intro(frm);
	},
});

frappe.ui.form.on("Assessment Scheme Category", {
	weight(frm) {
		update_weight_intro(frm);
	},
	active(frm) {
		update_weight_intro(frm);
	},
	include_in_final_grade(frm) {
		update_weight_intro(frm);
	},
});

function update_category_visibility(frm) {
	frm.toggle_display("categories", CATEGORY_METHODS.has(frm.doc.calculation_method));
}

function update_weight_intro(frm) {
	if (!CATEGORY_METHODS.has(frm.doc.calculation_method)) {
		frm.set_intro("");
		return;
	}

	const total = (frm.doc.categories || []).reduce((sum, row) => {
		if (!row.active || !row.include_in_final_grade) return sum;
		const weight = Number(row.weight || 0);
		return Number.isFinite(weight) ? sum + weight : sum;
	}, 0);
	const formattedTotal = format_weight_total(total);
	const template = __("Weighted category total: %(total)s%");
	const message = template.replace("%(total)s", formattedTotal);

	if (Math.abs(total - 100) <= 0.01) {
		frm.set_intro(message, "green");
		return;
	}

	frm.set_intro(message, "orange");
}

function format_weight_total(value) {
	if (Number.isInteger(value)) return String(value);
	return value.toFixed(2).replace(/\.?0+$/, "");
}
