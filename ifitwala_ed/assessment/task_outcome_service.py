# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/task_outcome_service.py

import frappe
from frappe import _


_GRADE_SCALE_CACHE = {}


def apply_official_outcome_from_contributions(outcome_id, policy=None):
	"""
	Recompute and persist the official outcome fields from contributions.
	"""
	return _recompute_official_outcome_internal(outcome_id, policy=policy)


def _recompute_official_outcome_internal(outcome_id, policy=None):
	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))

	outcome = frappe.db.get_value(
		"Task Outcome",
		outcome_id,
		[
			"task_delivery",
			"grade_scale",
			"is_published",
		],
		as_dict=True,
	)
	if not outcome:
		frappe.throw(_("Task Outcome not found."))

	was_published = int(outcome.get("is_published") or 0) == 1
	delivery = _get_delivery_context(outcome.get("task_delivery"))
	require_grading = int(delivery.get("require_grading") or 0)
	grading_mode = delivery.get("grading_mode")
	rubric_strategy = delivery.get("rubric_scoring_strategy")
	grade_scale = delivery.get("grade_scale") or outcome.get("grade_scale")
	rubric_version = delivery.get("rubric_version")

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

	selected = _select_official_contribution(contributions)

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
		if was_published:
			updates["is_published"] = 0
			updates["published_on"] = None
			updates["published_by"] = None
		frappe.db.set_value("Task Outcome", outcome_id, updates, update_modified=True)
		if grading_mode == "Criteria":
			_clear_outcome_criteria(outcome_id)
		return {"outcome": outcome_id, "grading_status": updates["grading_status"]}

	if grading_mode == "Criteria":
		_apply_official_criteria_from_contribution(outcome_id, selected.get("name"))
		result = _apply_criteria_official_fields(
			outcome_id=outcome_id,
			grade_scale=grade_scale,
			require_grading=require_grading,
			contribution=selected,
			rubric_scoring_strategy=rubric_strategy,
			rubric_version=rubric_version,
		)
		if was_published:
			_clear_outcome_publish(outcome_id)
		return result

	result = _apply_non_criteria_official_fields(
		outcome_id=outcome_id,
		grade_scale=grade_scale,
		require_grading=require_grading,
		contribution=selected,
	)
	if was_published:
		_clear_outcome_publish(outcome_id)
	return result


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


def set_procedural_status(outcome_id, status, note=None):
	"""
	Apply a procedural override safely and record an audit note.

	Full implementation is deferred to a later step.
	"""
	raise NotImplementedError("set_procedural_status is implemented in a later step.")


def _get_delivery_flags(delivery_id):
	if not delivery_id:
		return {}
	fields = [
		"grading_mode",
		"require_grading",
		"rubric_scoring_strategy",
		"grade_scale",
		"rubric_version",
	]
	return frappe.db.get_value("Task Delivery", delivery_id, fields, as_dict=True) or {}


def _get_delivery_context(delivery_id):
	return _get_delivery_flags(delivery_id)


def _select_official_contribution(contributions):
	moderator_types = {"Moderator"}
	self_types = {"Self", "Official Override"}

	for row in contributions:
		if row.get("contribution_type") in moderator_types:
			return row
	for row in contributions:
		if row.get("contribution_type") in self_types:
			return row
	return None


def _apply_non_criteria_official_fields(outcome_id, grade_scale, require_grading, contribution):
	grade_symbol = (contribution.get("grade") or "").strip()
	grade_value = contribution.get("grade_value")
	if grade_symbol:
		if not grade_scale:
			frappe.throw(_("Grade Scale is required to apply an official grade."))
		if grade_value in (None, ""):
			grade_value = resolve_grade_symbol(grade_scale, grade_symbol)
	else:
		grade_value = None

	official_fields = {
		"official_score": contribution.get("score"),
		"official_grade": grade_symbol or None,
		"official_grade_value": grade_value,
		"official_feedback": contribution.get("feedback"),
	}

	grading_status = "Moderated" if contribution.get("contribution_type") == "Moderator" else None
	if not grading_status:
		grading_status = "Finalized" if require_grading else "Not Applicable"

	official_fields["grading_status"] = grading_status
	frappe.db.set_value("Task Outcome", outcome_id, official_fields, update_modified=True)

	return {"outcome": outcome_id, "grading_status": grading_status}


def _apply_criteria_official_fields(
	outcome_id,
	grade_scale,
	require_grading,
	contribution,
	rubric_scoring_strategy,
	rubric_version=None,
):
	strategy = (rubric_scoring_strategy or "Sum Total").strip() or "Sum Total"
	official_feedback = contribution.get("feedback")

	if strategy == "Separate Criteria":
		updates = {
			"official_score": None,
			"official_grade": None,
			"official_grade_value": None,
			"official_feedback": official_feedback,
		}
	else:
		weights = _load_rubric_weights(rubric_version) if rubric_version else {}
		total_points = _sum_contribution_criterion_points(contribution.get("name"), weights)
		grade_symbol = _grade_symbol_from_score(grade_scale, total_points) if grade_scale else None
		grade_value = resolve_grade_symbol(grade_scale, grade_symbol) if grade_symbol and grade_scale else None
		updates = {
			"official_score": total_points,
			"official_grade": grade_symbol,
			"official_grade_value": grade_value,
			"official_feedback": official_feedback,
		}

	grading_status = "Moderated" if contribution.get("contribution_type") == "Moderator" else None
	if not grading_status:
		grading_status = "Finalized" if require_grading else "Not Applicable"

	updates["grading_status"] = grading_status
	frappe.db.set_value("Task Outcome", outcome_id, updates, update_modified=True)
	return {"outcome": outcome_id, "grading_status": grading_status}


def _grade_symbol_from_score(grade_scale, numeric_score):
	if numeric_score is None or grade_scale is None:
		return None

	grade_map = get_grade_scale_map(grade_scale)
	if not grade_map:
		return None

	selected = None
	selected_boundary = None
	for code, boundary in grade_map.items():
		try:
			boundary_value = float(boundary or 0)
		except Exception:
			boundary_value = 0.0
		if numeric_score >= boundary_value and (selected_boundary is None or boundary_value > selected_boundary):
			selected = code
			selected_boundary = boundary_value

	return selected


def _sum_contribution_criterion_points(contribution_name, weights=None):
	if not contribution_name:
		return 0.0

	rows = frappe.db.get_values(
		"Task Contribution Criterion",
		{
			"parent": contribution_name,
			"parenttype": "Task Contribution",
			"parentfield": "rubric_scores",
		},
		["assessment_criteria", "level_points"],
		as_dict=True,
	) or []
	total = 0.0
	for row in rows:
		criteria = row.get("assessment_criteria")
		weight = 1.0
		if weights and criteria in weights:
			weight = weights.get(criteria) or 1.0
		try:
			total += float(row.get("level_points") or 0) * float(weight or 1.0)
		except Exception:
			continue
	return total


def _apply_official_criteria_from_contribution(outcome_id, contribution_name):
	if not outcome_id or not contribution_name:
		return

	rows = frappe.db.get_values(
		"Task Contribution Criterion",
		{
			"parent": contribution_name,
			"parenttype": "Task Contribution",
			"parentfield": "rubric_scores",
		},
		["assessment_criteria", "level", "level_points", "feedback"],
		order_by="idx asc",
		as_dict=True,
	) or []

	frappe.db.delete(
		"Task Outcome Criterion",
		{
			"parent": outcome_id,
			"parenttype": "Task Outcome",
			"parentfield": "official_criteria",
		},
	)
	if not rows:
		return

	values = []
	idx = 1
	for row in rows:
		values.append({
			"name": frappe.generate_hash(length=10),
			"parent": outcome_id,
			"parenttype": "Task Outcome",
			"parentfield": "official_criteria",
			"idx": idx,
			"assessment_criteria": row.get("assessment_criteria"),
			"level": row.get("level"),
			"level_points": row.get("level_points") or 0,
			"feedback": row.get("feedback"),
		})
		idx += 1

	fields = ["name", "parent", "parenttype", "parentfield", "idx", "assessment_criteria", "level", "level_points", "feedback"]
	frappe.db.bulk_insert(
		doctype="Task Outcome Criterion",
		fields=fields,
		values=[[row.get(field) for field in fields] for row in values],
	)


def _clear_outcome_criteria(outcome_id):
	frappe.db.delete(
		"Task Outcome Criterion",
		{
			"parent": outcome_id,
			"parenttype": "Task Outcome",
			"parentfield": "official_criteria",
		},
	)


def _clear_outcome_publish(outcome_id):
	frappe.db.set_value(
		"Task Outcome",
		outcome_id,
		{
			"is_published": 0,
			"published_on": None,
			"published_by": None,
		},
		update_modified=True,
	)


def _load_rubric_weights(rubric_version):
	if not rubric_version:
		return {}

	rows = frappe.db.get_values(
		"Task Rubric Criterion",
		{
			"parent": rubric_version,
			"parenttype": "Task Rubric Version",
			"parentfield": "criteria",
		},
		["assessment_criteria", "criteria_weighting"],
		as_dict=True,
	) or []
	return {
		row.get("assessment_criteria"): row.get("criteria_weighting") or 1.0
		for row in rows
		if row.get("assessment_criteria")
	}


def mark_new_submission_seen(outcome_id):
	"""
	Clear the has_new_submission flag.
	"""
	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))

	frappe.db.set_value("Task Outcome", outcome_id, "has_new_submission", 0, update_modified=True)
	return {"ok": True, "outcome": outcome_id, "has_new_submission": 0}
