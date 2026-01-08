# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def _grade_scale_threshold_map(grade_scale, cache=None):
	if not grade_scale:
		frappe.throw(_("Grade Scale is required."))

	if cache is not None and grade_scale in cache:
		return cache[grade_scale]

	rows = frappe.db.get_all(
		"Grade Scale Interval",
		filters={"parent": grade_scale, "parenttype": "Grade Scale"},
		fields=["grade_code", "boundary_interval"],
	)

	grade_map = {}
	for row in rows:
		code = (row.get("grade_code") or "").strip()
		if not code:
			continue
		try:
			value = float(row.get("boundary_interval") or 0)
		except (TypeError, ValueError):
			value = 0.0
		grade_map[code] = value

	if cache is not None:
		cache[grade_scale] = grade_map
	return grade_map


def resolve_min_numeric_score(min_grade, grade_scale, cache=None):
	min_grade = (min_grade or "").strip()
	if not min_grade:
		return None

	try:
		return float(min_grade)
	except (TypeError, ValueError):
		pass

	grade_map = _grade_scale_threshold_map(grade_scale, cache=cache)
	if min_grade not in grade_map:
		frappe.throw(_("Min grade '{0}' not found in Grade Scale '{1}'.").format(min_grade, grade_scale))

	return grade_map[min_grade]
