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
	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))

	outcome = frappe.db.get_value(
		"Task Outcome",
		outcome_id,
		[
			"task_delivery",
			"grade_scale",
		],
		as_dict=True,
	)
	if not outcome:
		frappe.throw(_("Task Outcome not found."))

	contributions = frappe.db.get_values(
		"Task Contribution",
		{"task_outcome": outcome_id, "is_stale": 0, "status": ["!=", "Draft"]},
		[
			"name",
			"contribution_type",
			"score",
			"grade",
			"grade_value",
			"feedback",
			"moderation_action",
			"modified",
		],
		order_by="modified desc",
		as_dict=True,
	)

	moderator_types = {"Moderator"}
	self_types = {"Self", "Official Override"}

	selected = None
	for row in contributions:
		if row.get("contribution_type") in moderator_types:
			selected = row
			break

	if not selected:
		for row in contributions:
			if row.get("contribution_type") in self_types:
				selected = row
				break

	delivery = _get_delivery_flags(outcome.get("task_delivery"))
	require_grading = int(delivery.get("require_grading") or 0)
	grading_mode = delivery.get("grading_mode")

	if selected and selected.get("contribution_type") == "Moderator":
		if selected.get("moderation_action") == "Return to Grader":
			frappe.db.set_value(
				"Task Outcome",
				outcome_id,
				"grading_status",
				"In Progress",
				update_modified=True,
			)
			return {"outcome": outcome_id, "grading_status": "In Progress"}

	if not selected:
		updates = {
			"official_score": None,
			"official_grade": None,
			"official_grade_value": None,
			"official_feedback": None,
			"grading_status": "Not Applicable" if not require_grading else "Not Started",
		}
		frappe.db.set_value("Task Outcome", outcome_id, updates, update_modified=True)
		return {"outcome": outcome_id, "grading_status": updates["grading_status"]}

	grade_symbol = (selected.get("grade") or "").strip()
	grade_value = selected.get("grade_value")
	if grade_symbol:
		if not outcome.get("grade_scale"):
			frappe.throw(_("Grade Scale is required to apply an official grade."))
		if grade_value in (None, ""):
			grade_value = resolve_grade_symbol(outcome.get("grade_scale"), grade_symbol)
	else:
		grade_value = None

	official_fields = {
		"official_score": selected.get("score"),
		"official_grade": grade_symbol or None,
		"official_grade_value": grade_value,
		"official_feedback": selected.get("feedback"),
	}

	if selected.get("contribution_type") in moderator_types:
		grading_status = "Moderated"
	else:
		grading_status = "Finalized" if require_grading else "Not Applicable"

	official_fields["grading_status"] = grading_status
	frappe.db.set_value("Task Outcome", outcome_id, official_fields, update_modified=True)

	return {"outcome": outcome_id, "grading_status": grading_status}


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


def _get_delivery_flags(delivery_id):
	if not delivery_id:
		return {}
	fields = ["grading_mode", "require_grading"]
	return frappe.db.get_value("Task Delivery", delivery_id, fields, as_dict=True) or {}
