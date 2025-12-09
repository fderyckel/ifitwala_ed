# ifitwala_ed/ifitwala_ed/api/gradebook.py

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.data import flt, cint

from ifitwala_ed.api.student_groups import (
	TRIAGE_ROLES,
	_instructor_group_names,
	_user_roles,
)
from ifitwala_ed.assessment.gradebook_utils import get_levels_for_criterion


def _require_signed_in() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You need to sign in to access the gradebook."))
	return user


def _allowed_group_names(user: str) -> List[str] | None:
	"""Return list of group names the user can access, or None for full access."""
	roles = _user_roles(user)
	if roles & TRIAGE_ROLES:
		return None
	names = sorted(_instructor_group_names(user))
	return names or []


def _ensure_group_access(student_group: str) -> None:
	user = _require_signed_in()
	names = _allowed_group_names(user)
	if names is None:
		return
	if student_group not in names:
		frappe.throw(_("You do not have access to this student group."))


def _ensure_task_access(task_name: str) -> frappe._dict:
	if not task_name:
		frappe.throw(_("Task is required."))

	task = frappe.db.get_value(
		"Task",
		task_name,
		["name", "title", "student_group"],
		as_dict=True,
	)
	if not task:
		frappe.throw(_("Task {0} was not found.").format(task_name))
		return frappe._dict()

	_ensure_group_access(task.student_group)
	return task


@frappe.whitelist()
def fetch_groups(search: str | None = None, limit: int | None = 5) -> List[Dict[str, Any]]:
	"""
	Return the student groups visible to the current user with basic metadata.
	Optional search applies to group name or label.
	"""
	user = _require_signed_in()
	names = _allowed_group_names(user)

	filters: Dict[str, Any] = {}
	if names is not None:
		if not names:
			return []
		filters["name"] = ["in", names]

	fields = [
		"name",
		"student_group_name",
		"program",
		"course",
		"cohort",
		"academic_year",
	]

	# Default ordering is latest modified first
	order_by = "modified desc"
	limit_value = cint(limit) if limit else 0

	if search:
		search_value = search.strip()
		if search_value:
			filters["student_group_name"] = ["like", f"%{search_value}%"]
			# When searching, expand the window so admins can access more rows
			if limit_value and limit_value < 50:
				limit_value = 50
	else:
		# Without search, keep the window small for quick access
		if not limit_value:
			limit_value = 5

	get_all_kwargs: Dict[str, Any] = {
		"filters": filters,
		"fields": fields,
		"order_by": order_by,
	}
	if limit_value:
		get_all_kwargs["limit_page_length"] = limit_value

	groups = frappe.get_all("Student Group", **get_all_kwargs)

	if search:
		search_lower = search.strip().lower()
		if search_lower:
			groups = [
				row
				for row in groups
				if search_lower in (row.student_group_name or "").lower()
				or search_lower in (row.name or "").lower()
			]

	return [
		{
			"name": row.name,
			"label": row.student_group_name or row.name,
			"program": row.program,
			"course": row.course,
			"cohort": row.cohort,
			"academic_year": row.academic_year,
		}
		for row in groups
	]


@frappe.whitelist()
def fetch_group_tasks(student_group: str) -> Dict[str, Any]:
	"""
	Return tasks assigned to a student group with grading configuration.
	"""
	if not student_group:
		frappe.throw(_("Student Group is required."))

	_ensure_group_access(student_group)

	tasks = frappe.get_all(
		"Task",
		filters={"student_group": student_group},
		fields=[
			"name",
			"title",
			"due_date",
			"status",
			"is_graded",
			"points",
			"binary",
			"criteria",
			"observations",
			"max_points",
			"grade_scale",
			"task_type",
			"delivery_type",
			"available_from",
			"available_until",
			"is_published",
		],
		order_by="due_date desc, modified desc",
	)

	return {"tasks": [dict(row) for row in tasks]}


@frappe.whitelist()
def get_task_gradebook(task: str) -> Dict[str, Any]:
	"""
	Return gradebook payload for a task, including roster entries and criteria.
	"""
	task_info = _ensure_task_access(task)
	doc = frappe.get_doc("Task", task_info.name)

	criteria_payload: List[Dict[str, Any]] = []
	if doc.criteria:
		for row in doc.assessment_criteria:
			if not row.assessment_criteria:
				continue
			levels = get_levels_for_criterion(row.assessment_criteria) or []
			criteria_payload.append(
				{
					"name": row.name,
					"assessment_criteria": row.assessment_criteria,
					"criteria_name": row.criteria_name or row.assessment_criteria,
					"criteria_weighting": flt(row.criteria_weighting or 0),
					"levels": [
						{
							"level": level.get("level"),
							"points": flt(level.get("points") or 0),
						}
						for level in levels
					],
				}
			)

	student_rows = frappe.get_all(
		"Task Student",
		filters={"parent": doc.name, "parenttype": "Task"},
		fields=[
			"name",
			"student",
			"status",
			"complete",
			"mark_awarded",
			"feedback",
			"visible_to_student",
			"visible_to_guardian",
			"updated_on",
		],
		order_by="idx asc",
	)

	student_ids = [row.student for row in student_rows if row.student]
	student_meta: Dict[str, Dict[str, Any]] = {}
	if student_ids:
		for stu in frappe.get_all(
			"Student",
			filters={"name": ["in", student_ids]},
			fields=["name", "student_full_name", "student_preferred_name", "student_id", "student_image"],
		):
			student_meta[stu.name] = stu

	score_rows = frappe.get_all(
		"Task Criterion Score",
		filters={"parent": doc.name, "parenttype": "Task"},
		fields=["name", "student", "assessment_criteria", "level", "level_points", "feedback"],
	)

	score_map: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
	for score in score_rows:
		score_map[score.student][score.assessment_criteria] = {
			"name": score.name,
			"assessment_criteria": score.assessment_criteria,
			"level": score.level,
			"level_points": flt(score.level_points or 0),
			"feedback": score.feedback,
		}

	def _format_datetime(value: Any) -> str | None:
		if not value:
			return None
		return str(value)

	students_payload: List[Dict[str, Any]] = []
	for row in student_rows:
		meta = student_meta.get(row.student) or {}
		criteria_scores: List[Dict[str, Any]] = []
		for criterion in criteria_payload:
			score = score_map.get(row.student, {}).get(criterion["assessment_criteria"], {})
			criteria_scores.append(
				{
					"assessment_criteria": criterion["assessment_criteria"],
					"level": score.get("level"),
					"level_points": flt(score.get("level_points") or 0),
					"feedback": score.get("feedback"),
				}
			)

		students_payload.append(
			{
				"task_student": row.name,
				"student": row.student,
				"student_name": meta.get("student_full_name") or meta.get("student_preferred_name") or row.student,
				"student_preferred_name": meta.get("student_preferred_name"),
				"student_id": meta.get("student_id"),
				"student_image": meta.get("student_image"),
				"status": row.status,
				"complete": int(row.complete or 0),
				"mark_awarded": flt(row.mark_awarded) if row.mark_awarded is not None else None,
				"feedback": row.feedback,
				"visible_to_student": int(row.visible_to_student or 0),
				"visible_to_guardian": int(row.visible_to_guardian or 0),
				"updated_on": _format_datetime(row.updated_on),
				"criteria_scores": criteria_scores,
			}
		)

	task_payload = {
		"name": doc.name,
		"title": doc.title,
		"student_group": doc.student_group,
		"due_date": _format_datetime(doc.due_date),
		"is_graded": int(doc.is_graded or 0),
		"points": int(doc.points or 0),
		"binary": int(doc.binary or 0),
		"criteria": int(doc.criteria or 0),
		"observations": int(doc.observations or 0),
		"max_points": flt(doc.max_points or 0),
		"grade_scale": doc.grade_scale,
		"status": doc.status,
		"task_type": doc.task_type,
		"delivery_type": doc.delivery_type,
	}

	return {
		"task": task_payload,
		"criteria": criteria_payload,
		"students": students_payload,
	}


@frappe.whitelist()
def update_task_student(task_student: str, updates: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Update Task Student row (status, marks, visibility, etc.).
	"""
	if not task_student:
		frappe.throw(_("Task Student row is required."))

	if not isinstance(updates, dict):
		frappe.throw(_("Updates payload must be a dict."))

	doc = frappe.get_doc("Task Student", task_student)
	_ensure_task_access(doc.parent)

	allowed_fields = {
		"status",
		"mark_awarded",
		"feedback",
		"visible_to_student",
		"visible_to_guardian",
		"complete",
	}

	changed = False
	for field in allowed_fields:
		if field not in updates:
			continue
		value = updates[field]
		if field in {"visible_to_student", "visible_to_guardian", "complete"}:
			value = int(value or 0)
		if field in {"mark_awarded"}:
			value = flt(value) if value is not None else None
		if getattr(doc, field) != value:
			setattr(doc, field, value)
			changed = True

	# In points mode, mark_awarded is the canonical numeric grade.

	doc.updated_on = now_datetime().strftime("%Y-%m-%d %H:%M:%S")

	if changed:
		doc.save(ignore_permissions=False)

	return {
		"task_student": doc.name,
		"mark_awarded": doc.mark_awarded,
		"status": doc.status,
		"feedback": doc.feedback,
		"visible_to_student": doc.visible_to_student,
		"visible_to_guardian": doc.visible_to_guardian,
		"complete": doc.complete,
		"updated_on": doc.updated_on,
	}
