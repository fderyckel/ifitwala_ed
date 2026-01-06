# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


_GRADE_SCALE_CACHE = {}


def apply_official_outcome_from_contributions(outcome_id, policy=None):
	"""
	Recompute and persist the official outcome fields from contributions.

	Full implementation is deferred to Step 5.
	"""
	raise NotImplementedError("apply_official_outcome_from_contributions is implemented in Step 5.")


def get_grade_scale_map(grade_scale):
	if not grade_scale:
		frappe.throw(_("Grade Scale is required."))

	if grade_scale in _GRADE_SCALE_CACHE:
		return _GRADE_SCALE_CACHE[grade_scale]

	rows = frappe.db.get_values(
		"Grade Scale Interval",
		{"parent": grade_scale, "parenttype": "Grade Scale"},
		["grade_code", "boundary_interval"],
		as_dict=True,
	)

	grade_map = {}
	for row in rows:
		code = (row.get("grade_code") or "").strip()
		if not code:
			continue
		try:
			value = float(row.get("boundary_interval") or 0)
		except Exception:
			value = 0.0
		grade_map[code] = value

	_GRADE_SCALE_CACHE[grade_scale] = grade_map
	return grade_map


def resolve_grade_symbol(grade_scale, grade_symbol):
	grade_symbol = (grade_symbol or "").strip()
	if not grade_symbol:
		frappe.throw(_("Grade symbol is required."))

	grade_map = get_grade_scale_map(grade_scale)
	if grade_symbol not in grade_map:
		allowed = sorted(grade_map.keys())
		preview = ", ".join(allowed[:10])
		if len(allowed) > 10:
			preview = f"{preview}, ..."
		frappe.throw(
			_("Grade symbol '{0}' is not valid for scale {1}. Allowed: {2}")
			.format(grade_symbol, grade_scale, preview or _("(none configured)"))
		)

	return grade_map[grade_symbol]


def set_official_grade(outcome_id, grade_symbol, actor=None, note=None):
	outcome = frappe.get_doc("Task Outcome", outcome_id)

	if not getattr(outcome, "grade_scale", None):
		frappe.throw(_("Grade Scale is required to set an Official Grade."))

	value = resolve_grade_symbol(outcome.grade_scale, grade_symbol)
	outcome.official_grade = grade_symbol
	if outcome.meta.get_field("official_grade_value"):
		outcome.official_grade_value = value

	outcome.save(ignore_permissions=True)

	if note or actor:
		parts = []
		if actor:
			parts.append(f"Actor: {actor}")
		if note:
			parts.append(note)
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": outcome.doctype,
			"reference_name": outcome.name,
			"content": "Official grade set via service.\n" + "\n".join(parts),
		}).insert(ignore_permissions=True)

	return {
		"outcome": outcome.name,
		"official_grade": outcome.official_grade,
		"official_grade_value": outcome.official_grade_value,
	}


def set_procedural_status(outcome_id, status, note=None):
	"""
	Apply a procedural override safely and record an audit note.

	Full implementation is deferred to a later step.
	"""
	raise NotImplementedError("set_procedural_status is implemented in a later step.")
