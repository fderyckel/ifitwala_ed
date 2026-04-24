# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/task.py

# Task Planning API Controller (Teacher Planning Loop)
# - Search / Browse Task Library
# - Get Task Definitions
# - Create Task Delivery (Assign)
#
# REGRESSION TRAP:
# Controllers must not write official_* fields to Task Outcome.
# Use services (task_outcome_service, task_delivery_service) for all writes.

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.assessment import task_delivery_service
from ifitwala_ed.curriculum import planning as curriculum_planning

DEFAULT_TASK_SEARCH_LIMIT = 20
MAX_TASK_SEARCH_LIMIT = 100
TASK_LIBRARY_SCOPES = {"all", "mine", "shared"}


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _normalize_positive_int(value, *, default: int, label: str) -> int:
    if value in (None, ""):
        return default
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        frappe.throw(_("{0} must be a whole number.").format(label))
    if normalized < 0:
        frappe.throw(_("{0} cannot be negative.").format(label))
    return normalized


def _normalize_optional_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_search_scope(scope) -> str:
    normalized = _normalize_text(scope).lower() or "all"
    if normalized not in TASK_LIBRARY_SCOPES:
        frappe.throw(_("Unsupported task library scope: {scope}").format(scope=scope))
    return normalized


def _normalize_search_filters(filters) -> dict:
    if not filters:
        return {}
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)
    if not isinstance(filters, dict):
        frappe.throw(_("Task search filters must be a dict."))
    return filters


def _get_student_group_course(student_group: str) -> str:
    student_group = _normalize_text(student_group)
    if not student_group:
        frappe.throw(_("Student Group is required."))

    course = _normalize_text(frappe.db.get_value("Student Group", student_group, "course"))
    if not course:
        frappe.throw(_("Selected class is missing a course."))
    return course


def _resolve_task_library_course(*, student_group=None, course=None) -> str:
    student_group = _normalize_text(student_group)
    course = _normalize_text(course)

    group_course = _get_student_group_course(student_group) if student_group else ""
    if course and group_course and course != group_course:
        frappe.throw(_("Selected class does not belong to the chosen course."))
    resolved_course = course or group_course
    if not resolved_course:
        frappe.throw(_("Course context is required."))
    return resolved_course


def _assert_task_library_access(course: str, *, action_label: str, require_manage: bool = True) -> None:
    user = frappe.session.user
    roles = frappe.get_roles(user)
    if require_manage:
        curriculum_planning.assert_can_manage_course_curriculum(
            user,
            course,
            roles,
            action_label=action_label,
        )
        return

    curriculum_planning.assert_can_read_course_curriculum(
        user,
        course,
        roles,
        action_label=action_label,
    )


def _task_library_row(task: str) -> dict:
    task_name = _normalize_text(task)
    if not task_name:
        frappe.throw(_("Task is required."))

    row = frappe.db.get_value(
        "Task",
        task_name,
        [
            "name",
            "title",
            "instructions",
            "task_type",
            "default_course",
            "unit_plan",
            "is_template",
            "is_archived",
            "owner",
            "default_delivery_mode",
            "default_allow_feedback",
            "default_grading_mode",
            "default_rubric_scoring_strategy",
            "default_max_points",
            "default_grade_scale",
            "quiz_question_bank",
            "quiz_question_count",
            "quiz_time_limit_minutes",
            "quiz_max_attempts",
            "quiz_pass_percentage",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Task not found."))
    return row


def _task_visibility_scope(task_row: dict, user: str) -> str:
    if _normalize_text(task_row.get("owner")) == user:
        return "mine"
    if int(task_row.get("is_template") or 0):
        return "shared"
    return ""


def _assert_task_reusable_for_course(task_row: dict, course: str) -> str:
    course = _normalize_text(course)
    task_course = _normalize_text(task_row.get("default_course"))
    if not task_course:
        frappe.throw(_("Task is missing a course."))
    if task_course != course:
        frappe.throw(_("Task course does not match the selected class course."))

    visibility_scope = _task_visibility_scope(task_row, frappe.session.user)
    if visibility_scope:
        return visibility_scope

    frappe.throw(
        _("Only the task author can reuse this task until it is shared with the course task library."),
        frappe.PermissionError,
    )


def _task_grading_defaults(task_row: dict) -> dict:
    if _normalize_text(task_row.get("default_delivery_mode")) != "Assess":
        return {
            "default_allow_feedback": 0,
            "default_grading_mode": "None",
            "default_rubric_scoring_strategy": None,
            "default_max_points": None,
            "default_grade_scale": None,
        }
    return {
        "default_allow_feedback": task_row.get("default_allow_feedback"),
        "default_grading_mode": task_row.get("default_grading_mode"),
        "default_rubric_scoring_strategy": task_row.get("default_rubric_scoring_strategy"),
        "default_max_points": task_row.get("default_max_points"),
        "default_grade_scale": task_row.get("default_grade_scale"),
    }


def _load_assessment_criteria_meta(criteria_ids: list[str]) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    ids = [criteria_id for criteria_id in dict.fromkeys(criteria_ids or []) if _normalize_text(criteria_id)]
    if not ids:
        return {}, {}

    meta_rows = frappe.get_all(
        "Assessment Criteria",
        filters={"name": ["in", ids]},
        fields=["name", "assessment_criteria", "maximum_mark"],
        limit=0,
    )
    meta_map = {row.get("name"): row for row in meta_rows if row.get("name")}

    level_rows = frappe.get_all(
        "Assessment Criteria Level",
        filters={
            "parent": ["in", ids],
            "parenttype": "Assessment Criteria",
            "parentfield": "levels",
        },
        fields=["parent", "achievement_level"],
        order_by="idx asc",
        limit=0,
    )
    levels_map: dict[str, list[dict]] = {}
    for row in level_rows or []:
        parent = _normalize_text(row.get("parent"))
        level = _normalize_text(row.get("achievement_level"))
        if not parent or not level:
            continue
        levels_map.setdefault(parent, []).append({"level": level})

    return meta_map, levels_map


def _hydrate_criteria_rows(rows: list[dict] | None) -> list[dict]:
    normalized_rows = [row for row in (rows or []) if _normalize_text((row or {}).get("assessment_criteria"))]
    criteria_ids = [_normalize_text(row.get("assessment_criteria")) for row in normalized_rows]
    meta_map, levels_map = _load_assessment_criteria_meta(criteria_ids)

    payload = []
    for row in normalized_rows:
        criteria_id = _normalize_text(row.get("assessment_criteria"))
        meta = meta_map.get(criteria_id) or {}
        criteria_name = (
            _normalize_text(row.get("criteria_name")) or _normalize_text(meta.get("assessment_criteria")) or criteria_id
        )
        criteria_max_points = _normalize_optional_float(row.get("criteria_max_points"))
        if criteria_max_points is None:
            criteria_max_points = _normalize_optional_float(meta.get("maximum_mark"))
        payload.append(
            {
                "assessment_criteria": criteria_id,
                "criteria_name": criteria_name,
                "criteria_weighting": _normalize_optional_float(row.get("criteria_weighting")),
                "criteria_max_points": criteria_max_points,
                "levels": levels_map.get(criteria_id, []),
            }
        )
    return payload


def _get_course_assessment_criteria(course: str) -> list[dict]:
    rows = frappe.get_all(
        "Course Assessment Criteria",
        filters={
            "parent": course,
            "parenttype": "Course",
            "parentfield": "assessment_criteria",
        },
        fields=["assessment_criteria", "criteria_name", "criteria_weighting"],
        order_by="idx asc",
        limit=0,
    )
    return _hydrate_criteria_rows(rows)


def _get_task_criteria_defaults(task_name: str) -> list[dict]:
    task_name = _normalize_text(task_name)
    if not task_name:
        return []

    rows = frappe.get_all(
        "Task Template Criterion",
        filters={
            "parent": task_name,
            "parenttype": "Task",
            "parentfield": "task_criteria",
        },
        fields=["assessment_criteria", "criteria_weighting", "criteria_max_points"],
        order_by="idx asc",
        limit=0,
    )
    return _hydrate_criteria_rows(rows)


def _build_task_search_conditions(
    *, course: str, scope: str, query: str, unit_plan: str | None
) -> tuple[list[str], dict]:
    params = {
        "course": course,
        "user": frappe.session.user,
    }
    conditions = [
        "default_course = %(course)s",
        "COALESCE(is_archived, 0) = 0",
    ]

    if scope == "mine":
        conditions.append("owner = %(user)s")
    elif scope == "shared":
        conditions.append("COALESCE(is_template, 0) = 1")
    else:
        conditions.append("(owner = %(user)s OR COALESCE(is_template, 0) = 1)")

    if query:
        params["query"] = f"%{query}%"
        conditions.append("title LIKE %(query)s")

    if unit_plan:
        params["unit_plan"] = unit_plan

    return conditions, params


def _search_reusable_tasks(*, course: str, query: str, scope: str, limit: int, start: int, unit_plan: str | None):
    conditions, params = _build_task_search_conditions(
        course=course,
        scope=scope,
        query=query,
        unit_plan=unit_plan,
    )
    order_parts = [
        "CASE WHEN owner = %(user)s THEN 0 ELSE 1 END",
    ]
    if unit_plan:
        order_parts.append("CASE WHEN COALESCE(unit_plan, '') = %(unit_plan)s THEN 0 ELSE 1 END")
    order_parts.append("modified DESC")

    params.update(
        {
            "limit": limit,
            "start": start,
        }
    )

    rows = frappe.db.sql(
        f"""
        SELECT
            name,
            title,
            task_type,
            default_course,
            unit_plan,
            owner,
            COALESCE(is_template, 0) AS is_template,
            modified
        FROM `tabTask`
        WHERE {" AND ".join(conditions)}
        ORDER BY {", ".join(order_parts)}
        LIMIT %(limit)s OFFSET %(start)s
        """,
        params,
        as_dict=True,
    )

    user = frappe.session.user
    normalized_rows = []
    for row in rows or []:
        visibility_scope = _task_visibility_scope(row, user)
        if not visibility_scope:
            continue
        normalized_rows.append(
            {
                "name": row.get("name"),
                "title": row.get("title"),
                "task_type": row.get("task_type"),
                "default_course": row.get("default_course"),
                "unit_plan": row.get("unit_plan"),
                "owner": row.get("owner"),
                "is_template": int(row.get("is_template") or 0),
                "modified": row.get("modified"),
                "visibility_scope": visibility_scope,
                "visibility_label": "Shared with course team" if visibility_scope == "shared" else "Your task",
            }
        )
    return normalized_rows


@frappe.whitelist()
def search_tasks(filters=None, query=None, limit=20, start=0):
    """
    Search reusable tasks for one course-scoped assignment workflow.
    """
    filters = _normalize_search_filters(filters)
    course = _resolve_task_library_course(
        student_group=filters.get("student_group"),
        course=filters.get("course") or filters.get("default_course"),
    )
    _assert_task_library_access(course, action_label="reuse tasks for this course")

    return _search_reusable_tasks(
        course=course,
        query=_normalize_text(query),
        scope=_normalize_search_scope(filters.get("scope")),
        limit=min(
            _normalize_positive_int(limit, default=DEFAULT_TASK_SEARCH_LIMIT, label=_("Limit")),
            MAX_TASK_SEARCH_LIMIT,
        ),
        start=_normalize_positive_int(start, default=0, label=_("Start")),
        unit_plan=_normalize_text(filters.get("unit_plan")) or None,
    )


@frappe.whitelist()
def search_reusable_tasks(student_group=None, course=None, unit_plan=None, query=None, scope=None, limit=20, start=0):
    resolved_course = _resolve_task_library_course(student_group=student_group, course=course)
    _assert_task_library_access(resolved_course, action_label="reuse tasks for this course")

    return _search_reusable_tasks(
        course=resolved_course,
        query=_normalize_text(query),
        scope=_normalize_search_scope(scope),
        limit=min(
            _normalize_positive_int(limit, default=DEFAULT_TASK_SEARCH_LIMIT, label=_("Limit")),
            MAX_TASK_SEARCH_LIMIT,
        ),
        start=_normalize_positive_int(start, default=0, label=_("Start")),
        unit_plan=_normalize_text(unit_plan) or None,
    )


@frappe.whitelist()
def get_task_for_delivery(task, student_group=None, course=None):
    """
    Get Task details payload for the Assign Wizard.
    """
    task_row = _task_library_row(task)
    resolved_course = _resolve_task_library_course(
        student_group=student_group,
        course=course or task_row.get("default_course"),
    )
    _assert_task_library_access(resolved_course, action_label="reuse tasks for this course")
    visibility_scope = _assert_task_reusable_for_course(task_row, resolved_course)

    # Minimal payload for the wizard
    return {
        "name": task_row.get("name"),
        "title": task_row.get("title"),
        "description": task_row.get("instructions"),
        "instructions": task_row.get("instructions"),
        "task_type": task_row.get("task_type"),
        "default_course": task_row.get("default_course"),
        "unit_plan": task_row.get("unit_plan"),
        "is_template": int(task_row.get("is_template") or 0),
        "owner": task_row.get("owner"),
        "visibility_scope": visibility_scope,
        "grading_defaults": _task_grading_defaults(task_row),
        "criteria_defaults": {
            "rubric_scoring_strategy": task_row.get("default_rubric_scoring_strategy"),
            "criteria_rows": _get_task_criteria_defaults(task_row.get("name")),
        },
        "default_delivery_mode": task_row.get("default_delivery_mode"),
        "quiz_defaults": {
            "quiz_question_bank": task_row.get("quiz_question_bank"),
            "quiz_question_count": task_row.get("quiz_question_count"),
            "quiz_time_limit_minutes": task_row.get("quiz_time_limit_minutes"),
            "quiz_max_attempts": task_row.get("quiz_max_attempts"),
            "quiz_pass_percentage": task_row.get("quiz_pass_percentage"),
        },
    }


@frappe.whitelist()
def list_course_assessment_criteria(student_group=None, course=None):
    resolved_course = _resolve_task_library_course(student_group=student_group, course=course)
    _assert_task_library_access(resolved_course, action_label="configure criteria for this course")
    return _get_course_assessment_criteria(resolved_course)


@frappe.whitelist()
def create_task_delivery(payload):
    """
    Orchestrate Task Delivery creation.
    Delegates strictly to task_delivery_service.
    """
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("Delivery payload must be a dict."))
    if not _can_manage_tasks():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    planning_context = task_delivery_service.resolve_planning_context(
        payload.get("student_group"),
        payload.get("class_teaching_plan"),
        payload.get("class_session"),
    )
    course = _normalize_text(planning_context.get("course"))
    _assert_task_library_access(course, action_label="assign work for this course")

    task_row = _task_library_row(payload.get("task"))
    _assert_task_reusable_for_course(task_row, course)

    return task_delivery_service.create_delivery(payload)


def _has_role(*roles):
    user_roles = set(frappe.get_roles(frappe.session.user))
    return any(r in user_roles for r in roles)


def _can_manage_tasks():
    # Allow Instructors, Curriculum Coordinators, Academic Admins
    return _has_role("System Manager", "Academic Admin", "Curriculum Coordinator", "Instructor")
