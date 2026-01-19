# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/gradebook.py

# Gradebook API Controller (Teacher Grading Loop)
# - Get Gradebook Grid (read-only optimization)
# - Get Grading Drawer (Outcome + Submissions + History)
# - Actions: Save Draft, Submit, Moderate (via Services)
#
# REGRESSION TRAP:
# Controllers must not write official_* fields to Task Outcome.
# Use task_outcome_service or task_contribution_service for all writes.

from __future__ import annotations

import frappe
from frappe import _
from ifitwala_ed.assessment import task_contribution_service
from ifitwala_ed.assessment import task_outcome_service
from ifitwala_ed.assessment import task_submission_service


# ---------------------------
# Public endpoints (UI)
# ---------------------------

@frappe.whitelist()
def get_grid(filters=None, **kwargs):
	"""
	Grid = Task Outcome rows for deliveries in scope.
	"""
	if not _can_read_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	data = _normalize_filters(filters, kwargs)
	school = data.get("school")
	academic_year = data.get("academic_year")
	course = data.get("course")
	_require(school, "School")
	_require(academic_year, "Academic Year")

	scope = _resolve_gradebook_scope(school, academic_year, course)
	is_instructor_scoped = _is_instructor_scoped_user()
	delivery_filters = {
		"school": school,
		"academic_year": academic_year,
	}
	if is_instructor_scoped:
		if not scope.get("student_groups"):
			frappe.throw(_("No instructor teaching scope found."))
		delivery_filters["student_group"] = ["in", scope["student_groups"]]
	elif scope.get("student_groups"):
		delivery_filters["student_group"] = ["in", scope["student_groups"]]
	if scope.get("courses"):
		delivery_filters["course"] = ["in", scope["courses"]]

	deliveries = frappe.get_all(
		"Task Delivery",
		filters=delivery_filters,
		fields=[
			"name",
			"task",
			"grading_mode",
			"rubric_scoring_strategy",
			"due_date",
		],
		order_by="due_date asc, name asc",
		limit_page_length=0,
	)
	if not deliveries:
		return {"deliveries": [], "students": [], "cells": []}

	task_titles = _get_task_titles([row.get("task") for row in deliveries])
	delivery_map = {}
	for row in deliveries:
		delivery_map[row["name"]] = row

	delivery_payload = []
	for row in deliveries:
		delivery_payload.append({
			"delivery_id": row.get("name"),
			"task_title": task_titles.get(row.get("task")) or row.get("task"),
			"grading_mode": row.get("grading_mode"),
			"rubric_scoring_strategy": row.get("rubric_scoring_strategy"),
			"due_date": row.get("due_date"),
		})

	outcomes = frappe.get_all(
		"Task Outcome",
		filters={"task_delivery": ["in", list(delivery_map.keys())]},
		fields=[
			"name",
			"task_delivery",
			"student",
			"grading_status",
			"procedural_status",
			"has_submission",
			"has_new_submission",
			"official_score",
			"official_grade",
			"official_grade_value",
		],
		order_by="student asc, task_delivery asc",
		limit_page_length=0,
	)

	student_ids = [row.get("student") for row in outcomes if row.get("student")]
	student_map = _get_student_display_map(student_ids)
	students = _build_student_payload(student_ids, student_map)

	criteria_outcome_ids = {
		row.get("name")
		for row in outcomes
		if delivery_map.get(row.get("task_delivery"), {}).get("grading_mode") == "Criteria"
	}
	criteria_map = _get_outcome_criteria_map(criteria_outcome_ids)

	cells = []
	for row in outcomes:
		outcome_id = row.get("name")
		delivery_id = row.get("task_delivery")
		delivery = delivery_map.get(delivery_id, {})
		cell = {
			"outcome_id": outcome_id,
			"student_id": row.get("student"),
			"delivery_id": delivery_id,
			"flags": {
				"has_submission": _bool_flag(row.get("has_submission")),
				"has_new_submission": _bool_flag(row.get("has_new_submission")),
				"grading_status": row.get("grading_status"),
				"procedural_status": row.get("procedural_status"),
			},
			"official": {
				"score": row.get("official_score"),
				"grade": row.get("official_grade"),
				"grade_value": row.get("official_grade_value"),
			},
		}
		if delivery.get("grading_mode") == "Criteria":
			cell["official"]["criteria"] = criteria_map.get(outcome_id, [])
		cells.append(cell)

	return {
		"deliveries": delivery_payload,
		"students": students,
		"cells": cells,
	}


@frappe.whitelist()
def get_drawer(outcome_id: str):
	"""
	Drawer payload for a single outcome.
	"""
	_require(outcome_id, "Task Outcome")

	if not _can_read_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	# Fetch Outcome
	outcome_fields = [
		"name",
		"task_delivery",
		"grading_status",
		"procedural_status",
		"official_score",
		"official_grade",
		"official_grade_value",
		"official_feedback",
	]
	outcome_doc = frappe.db.get_value("Task Outcome", outcome_id, outcome_fields, as_dict=True)
	if not outcome_doc:
		frappe.throw(_("Task Outcome not found."))

	outcome_criteria = _get_outcome_criteria_map({outcome_id}).get(outcome_id, [])

	# Fetch Submissions
	submissions = frappe.get_all(
		"Task Submission",
		filters={"task_outcome": outcome_id},
		fields=[
			"name",
			"version",
			"submitted_on",
			"submitted_by",
			"is_late",
			"is_cloned",
			"cloned_from",
			"submission_origin",
			"is_stub",
			"evidence_note",
			"link_url",
			"text_content",
			"attachments",
		],
		order_by="version desc",
		limit_page_length=20,
	)

	contributions = frappe.get_all(
		"Task Contribution",
		filters={"task_outcome": outcome_id},
		fields=[
			"name",
			"contributor",
			"contribution_type",
			"status",
			"is_stale",
			"task_submission",
			"score",
			"grade",
			"grade_value",
			"feedback",
			"moderation_action",
			"submitted_on",
			"modified",
		],
		order_by="submitted_on desc, modified desc",
		limit_page_length=100,
	)

	my_contribution = _select_my_contribution(contributions)
	my_criteria = []
	if my_contribution:
		my_criteria = _get_contribution_criteria(my_contribution.get("name"))

	moderation_history = _build_moderation_history(contributions)
	submission_versions = [
		{
			"submission_id": row.get("name"),
			"version": row.get("version"),
			"submitted_on": row.get("submitted_on"),
			"origin": row.get("submission_origin"),
			"is_stub": _bool_flag(row.get("is_stub")),
		}
		for row in sorted(submissions, key=lambda r: r.get("version") or 0)
	]
	latest_submission = submissions[0] if submissions else None
	if latest_submission:
		latest_submission = {
			"submission_id": latest_submission.get("name"),
			"version": latest_submission.get("version"),
			"submitted_on": latest_submission.get("submitted_on"),
			"origin": latest_submission.get("submission_origin"),
			"is_stub": _bool_flag(latest_submission.get("is_stub")),
		}

	return {
		"outcome": {
			"outcome_id": outcome_doc.get("name"),
			"grading_status": outcome_doc.get("grading_status"),
			"procedural_status": outcome_doc.get("procedural_status"),
			"official": {
				"score": outcome_doc.get("official_score"),
				"grade": outcome_doc.get("official_grade"),
				"grade_value": outcome_doc.get("official_grade_value"),
				"feedback": outcome_doc.get("official_feedback"),
			},
			"criteria": outcome_criteria,
		},
		"latest_submission": latest_submission,
		"submission_versions": submission_versions,
		"my_contribution": {
			"status": my_contribution.get("status"),
			"criteria": my_criteria,
			"feedback": my_contribution.get("feedback"),
		} if my_contribution else None,
		"moderation_history": moderation_history,
		"submissions": submissions,
		"contributions": contributions,
	}


@frappe.whitelist()
def save_draft(payload=None, **kwargs):
	"""
	Save a draft contribution (no direct Outcome writes).
	"""
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	data = _normalize_payload(payload, kwargs)
	_reject_official_fields(data)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	_require(outcome_id, "Task Outcome")
	submission_id = _get_existing_submission_id(outcome_id, data)
	if submission_id:
		data["task_submission"] = submission_id
	result = task_contribution_service.save_draft_contribution(data, contributor=frappe.session.user)
	return {
		"result": result,
		"outcome": _get_outcome_summary(outcome_id),
	}


@frappe.whitelist()
def submit_contribution(payload=None, **kwargs):
	"""
	Submit a contribution (no direct Outcome writes).
	"""
	if not _can_write_gradebook():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	data = _normalize_payload(payload, kwargs)
	_reject_official_fields(data)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	_require(outcome_id, "Task Outcome")
	data["task_submission"] = _resolve_or_create_stub_submission_id(outcome_id, data)
	result = task_contribution_service.submit_contribution(data, contributor=frappe.session.user)
	return {
		"ok": True,
		"outcome_update": result.get("outcome_update"),
		"result": result,
	}


@frappe.whitelist()
def save_contribution_draft(payload=None, **kwargs):
	return save_draft(payload=payload, **kwargs)


@frappe.whitelist()
def moderator_action(payload=None, **kwargs):
	"""
	Moderator action (Approve/Return/etc) via contributions.
	"""
	if not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	data = _normalize_payload(payload, kwargs)
	_reject_official_fields(data)
	outcome_id = _get_payload_value(data, "task_outcome", "outcome")
	_require(outcome_id, "Task Outcome")
	data["task_submission"] = _resolve_or_create_stub_submission_id(outcome_id, data)
	result = task_contribution_service.apply_moderator_action(data, contributor=frappe.session.user)
	return {
		"ok": True,
		"outcome_update": result.get("outcome_update"),
		"result": result,
	}


@frappe.whitelist()
def mark_new_submission_seen(outcome: str):
	"""
	Clear 'New Evidence' flag.
	"""
	_require(outcome, "Task Outcome")
	if not _can_write_gradebook() and not _is_academic_adminish():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	return task_outcome_service.mark_new_submission_seen(outcome)


# ---------------------------
# Helpers
# ---------------------------

def _normalize_filters(filters, kwargs):
	data = filters if filters is not None else kwargs
	if isinstance(data, str):
		data = frappe.parse_json(data)
	if not isinstance(data, dict):
		frappe.throw(_("Filters must be a dict."))
	return data


def _normalize_payload(payload, kwargs):
	data = payload if payload is not None else kwargs
	if isinstance(data, str):
		data = frappe.parse_json(data)
	if not isinstance(data, dict) or not data:
		frappe.throw(_("Payload must be a dict."))
	return data


def _resolve_gradebook_scope(school, academic_year, course):
	user = frappe.session.user
	is_instructor_scoped = _is_instructor_scoped_user()
	if not is_instructor_scoped:
		return {
			"courses": [course] if course else [],
			"student_groups": [],
		}

	group_names = _instructor_group_names(user)
	if not group_names:
		frappe.throw(_("No instructor teaching scope found."))

	group_filters = {
		"name": ["in", list(group_names)],
		"school": school,
		"academic_year": academic_year,
	}
	if course:
		group_filters["course"] = course

	groups = frappe.get_all(
		"Student Group",
		filters=group_filters,
		fields=["name", "course"],
		limit_page_length=0,
	)
	if not groups:
		frappe.throw(_("No student groups found for the provided filters."))

	courses = sorted({row.get("course") for row in groups if row.get("course")})
	if not course and not courses:
		frappe.throw(_("No courses found for instructor scope."))

	return {
		"courses": courses or ([course] if course else []),
		"student_groups": [row.get("name") for row in groups if row.get("name")],
	}


def _instructor_group_names(user):
	names = set()
	for row in frappe.get_all(
		"Student Group Instructor",
		filters={"user_id": user},
		pluck="parent",
	):
		names.add(row)

	instructor_ids = frappe.get_all("Instructor", filters={"linked_user_id": user}, pluck="name")
	if instructor_ids:
		for row in frappe.get_all(
			"Student Group Instructor",
			filters={"instructor": ["in", instructor_ids]},
			pluck="parent",
		):
			names.add(row)

	employee = frappe.db.get_value(
		"Employee", {"user_id": user, "status": "Active"}, "name"
	)
	if employee:
		for row in frappe.get_all(
			"Student Group Instructor",
			filters={"employee": employee},
			pluck="parent",
		):
			names.add(row)

	return names


def _get_task_titles(task_ids):
	task_ids = [task_id for task_id in set(task_ids or []) if task_id]
	if not task_ids:
		return {}

	rows = frappe.get_all(
		"Task",
		filters={"name": ["in", task_ids]},
		fields=["name", "title"],
		limit_page_length=0,
	)
	return {row.get("name"): row.get("title") for row in rows}


def _build_student_payload(student_ids, student_map):
	unique_ids = {student_id for student_id in student_ids if student_id}
	ordered = sorted(unique_ids, key=lambda sid: student_map.get(sid) or sid)
	return [
		{
			"student_id": student_id,
			"student_name": student_map.get(student_id) or student_id,
		}
		for student_id in ordered
	]


def _get_outcome_criteria_map(outcome_ids):
	outcome_ids = {oid for oid in (outcome_ids or set()) if oid}
	if not outcome_ids:
		return {}

	rows = frappe.get_all(
		"Task Outcome Criterion",
		filters={
			"parent": ["in", list(outcome_ids)],
			"parenttype": "Task Outcome",
			"parentfield": "official_criteria",
		},
		fields=["parent", "assessment_criteria", "level", "level_points"],
		order_by="idx asc",
		limit_page_length=0,
	)
	criteria_map = {}
	for row in rows:
		parent = row.get("parent")
		if not parent:
			continue
		criteria_map.setdefault(parent, []).append({
			"criteria": row.get("assessment_criteria"),
			"level": row.get("level"),
			"points": row.get("level_points"),
		})
	return criteria_map


def _select_my_contribution(contributions):
	current_user = frappe.session.user
	draft = None
	submitted = None
	for row in contributions:
		if row.get("contributor") != current_user:
			continue
		if row.get("status") == "Draft" and not draft:
			draft = row
		if row.get("status") == "Submitted" and not submitted:
			submitted = row
		if draft and submitted:
			break
	return draft or submitted


def _get_contribution_criteria(contribution_id):
	if not contribution_id:
		return []
	rows = frappe.get_all(
		"Task Contribution Criterion",
		filters={
			"parent": contribution_id,
			"parenttype": "Task Contribution",
			"parentfield": "rubric_scores",
		},
		fields=["assessment_criteria", "level", "level_points"],
		order_by="idx asc",
		limit_page_length=0,
	)
	return [
		{
			"criteria": row.get("assessment_criteria"),
			"level": row.get("level"),
			"points": row.get("level_points"),
		}
		for row in rows
	]


def _build_moderation_history(contributions):
	history = []
	for row in contributions:
		if row.get("contribution_type") != "Moderator":
			continue
		history.append({
			"by": row.get("contributor") or "Moderator",
			"action": row.get("moderation_action"),
			"on": row.get("submitted_on") or row.get("modified"),
		})
	return history


def _bool_flag(value):
	return bool(int(value or 0))


def _require(value, label):
	if not value:
		frappe.throw(_("{0} is required.").format(label))


def _has_role(*roles):
	user_roles = set(frappe.get_roles(frappe.session.user))
	return any(role in user_roles for role in roles)


def _is_academic_adminish():
	return _has_role("System Manager", "Academic Admin", "Academic Assistant", "Curriculum Coordinator")


def _is_instructor_scoped_user():
	return _has_role("Instructor") and not _is_academic_adminish()


def _can_read_gradebook():
	return _can_write_gradebook() or _is_academic_adminish() or _has_role("Academic Staff")


def _can_write_gradebook():
	return _has_role("System Manager", "Academic Admin", "Curriculum Coordinator", "Instructor")


def _get_student_display_map(student_ids):
	if not student_ids:
		return {}

	meta = frappe.get_meta("Student")
	fields = ["name"]
	if meta.get_field("student_name"):
		fields.append("student_name")
	elif meta.get_field("full_name"):
		fields.append("full_name")
	else:
		if meta.get_field("first_name"):
			fields.append("first_name")
		if meta.get_field("last_name"):
			fields.append("last_name")

	rows = frappe.get_all(
		"Student",
		filters={"name": ["in", list(set(student_ids))]},
		fields=fields,
		limit_page_length=0,
	)

	out = {}
	for row in rows:
		label = row.get("student_name") or row.get("full_name")
		if not label:
			fn = (row.get("first_name") or "").strip()
			ln = (row.get("last_name") or "").strip()
			label = (fn + " " + ln).strip() or row["name"]
		out[row["name"]] = label

	return out


def _get_outcome_summary(outcome_id):
	if not outcome_id:
		return None

	fields = [
		"name",
		"grading_status",
		"procedural_status",
		"has_submission",
		"has_new_submission",
	]
	return frappe.db.get_value("Task Outcome", outcome_id, fields, as_dict=True)


def _reject_official_fields(payload):
	if not isinstance(payload, dict):
		return
	for key in payload.keys():
		if key.startswith("official_"):
			frappe.throw(_("official_* fields are not accepted in gradebook endpoints."))


def _get_payload_value(data, *keys):
	for key in keys:
		if key in data and data.get(key) not in (None, ""):
			return data.get(key)
	return None


def _get_existing_submission_id(outcome_id, payload):
	submission_id = _get_payload_value(payload, "task_submission", "submission")
	if submission_id:
		return submission_id

	latest = frappe.get_all(
		"Task Submission",
		filters={"task_outcome": outcome_id},
		fields=["name", "version", "is_stub"],
		order_by="version desc",
		limit_page_length=1,
	)
	if latest:
		return latest[0]["name"]

	return None


def _resolve_or_create_stub_submission_id(outcome_id, payload):
	submission_id = _get_existing_submission_id(outcome_id, payload)
	if submission_id:
		return submission_id

	return task_submission_service.ensure_evidence_stub_submission(
		outcome_id,
		origin="Teacher Observation",
		note=payload.get("evidence_note"),
	)
