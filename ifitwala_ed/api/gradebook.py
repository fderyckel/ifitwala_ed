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
from frappe.utils import now_datetime

from ifitwala_ed.assessment import task_contribution_service, task_outcome_service, task_submission_service
from ifitwala_ed.utilities.image_utils import apply_preferred_student_images

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
        limit=0,
    )
    if not deliveries:
        return {"deliveries": [], "students": [], "cells": []}

    task_titles = _get_task_titles([row.get("task") for row in deliveries])
    delivery_map = {}
    for row in deliveries:
        delivery_map[row["name"]] = row

    delivery_payload = []
    for row in deliveries:
        delivery_payload.append(
            {
                "delivery_id": row.get("name"),
                "task_title": task_titles.get(row.get("task")) or row.get("task"),
                "grading_mode": row.get("grading_mode"),
                "rubric_scoring_strategy": row.get("rubric_scoring_strategy"),
                "due_date": row.get("due_date"),
            }
        )

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
        limit=0,
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
        limit=20,
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
        limit=100,
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
        }
        if my_contribution
        else None,
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
# Compatibility endpoints (current Staff Gradebook page)
# ---------------------------


@frappe.whitelist()
def fetch_groups(
    search: str | None = None,
    limit: int | None = None,
    school: str | None = None,
    academic_year: str | None = None,
    program: str | None = None,
    course: str | None = None,
):
    """
    Return visible student groups for current gradebook users.
    Compatibility shape for existing Gradebook.vue.
    """
    if not _can_read_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    filters = {}
    if school:
        filters["school"] = school
    if academic_year:
        filters["academic_year"] = academic_year
    if program:
        filters["program"] = program
    if course:
        filters["course"] = course

    if _is_instructor_scoped_user():
        names = sorted(_instructor_group_names(frappe.session.user))
        if not names:
            return []
        filters["name"] = ["in", names]

    rows = frappe.get_all(
        "Student Group",
        filters=filters,
        fields=[
            "name",
            "student_group_name",
            "school",
            "program",
            "course",
            "cohort",
            "academic_year",
        ],
        order_by="student_group_name asc, name asc",
        limit=0,
    )

    if search:
        needle = str(search).strip().lower()
        if needle:
            rows = [
                row
                for row in rows
                if needle in str(row.get("student_group_name") or "").lower()
                or needle in str(row.get("name") or "").lower()
            ]

    cap = None
    if limit not in (None, ""):
        try:
            cap = max(1, min(int(limit), 500))
        except Exception:
            cap = 100
    if cap is not None:
        rows = rows[:cap]

    return [
        {
            "name": row.get("name"),
            "label": row.get("student_group_name") or row.get("name"),
            "school": row.get("school"),
            "program": row.get("program"),
            "course": row.get("course"),
            "cohort": row.get("cohort"),
            "academic_year": row.get("academic_year"),
        }
        for row in rows
        if row.get("name")
    ]


@frappe.whitelist()
def fetch_group_tasks(student_group: str):
    """
    Return delivery rows (task list) for a student group.
    Compatibility shape for existing Gradebook.vue.
    """
    if not _can_read_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    _require(student_group, "Student Group")
    _assert_group_access(student_group)

    deliveries = frappe.get_all(
        "Task Delivery",
        filters={"student_group": student_group},
        fields=[
            "name",
            "task",
            "due_date",
            "delivery_mode",
            "grading_mode",
            "allow_feedback",
            "max_points",
            "rubric_scoring_strategy",
        ],
        order_by="due_date desc, modified desc",
        limit=0,
    )

    task_ids = [row.get("task") for row in deliveries if row.get("task")]
    task_map = {}
    if task_ids:
        task_rows = frappe.get_all(
            "Task",
            filters={"name": ["in", task_ids]},
            fields=["name", "title", "task_type"],
            limit=0,
        )
        task_map = {row.get("name"): row for row in task_rows if row.get("name")}

    tasks = []
    for delivery in deliveries:
        grading_mode = (delivery.get("grading_mode") or "").strip()
        delivery_mode = (delivery.get("delivery_mode") or "").strip()
        task_row = task_map.get(delivery.get("task")) or {}
        tasks.append(
            {
                "name": delivery.get("name"),  # Task Delivery id (compat key consumed by Gradebook.vue)
                "title": task_row.get("title") or delivery.get("task"),
                "due_date": delivery.get("due_date"),
                "status": None,
                "grading_mode": grading_mode or None,
                "allow_feedback": 1 if _bool_flag(delivery.get("allow_feedback")) else 0,
                "rubric_scoring_strategy": delivery.get("rubric_scoring_strategy") or None,
                "points": 1 if grading_mode == "Points" else 0,
                "binary": 1 if grading_mode in {"Binary", "Completion"} else 0,
                "criteria": 1 if grading_mode == "Criteria" else 0,
                "observations": 1 if delivery_mode in {"Assign Only", "Collect Work"} else 0,
                "max_points": _coerce_float(delivery.get("max_points")),
                "task_type": task_row.get("task_type"),
                "delivery_type": delivery_mode or None,
            }
        )

    return {"tasks": tasks}


@frappe.whitelist()
def get_task_gradebook(task: str):
    """
    Return student grading payload for a Task Delivery.
    Compatibility shape for existing Gradebook.vue.
    """
    if not _can_read_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    _require(task, "Task Delivery")

    delivery = _resolve_delivery(task)
    _assert_group_access(delivery.get("student_group"))

    task_row = frappe.db.get_value(
        "Task",
        delivery.get("task"),
        ["name", "title", "task_type"],
        as_dict=True,
    ) or {"name": delivery.get("task"), "title": delivery.get("task")}

    criteria_payload = _build_delivery_criteria_payload(delivery)

    outcomes = frappe.get_all(
        "Task Outcome",
        filters={"task_delivery": delivery.get("name")},
        fields=[
            "name",
            "student",
            "grading_status",
            "is_complete",
            "official_score",
            "official_feedback",
            "is_published",
            "modified",
        ],
        order_by="student asc",
        limit=0,
    )
    outcome_ids = [row.get("name") for row in outcomes if row.get("name")]
    outcome_criteria = _get_outcome_criteria_rows(outcome_ids)

    student_ids = [row.get("student") for row in outcomes if row.get("student")]
    student_display_map = _get_student_display_map(student_ids)
    student_meta_map = _get_student_meta_map(student_ids)

    students_payload = []
    for outcome in outcomes:
        student_id = outcome.get("student")
        meta = student_meta_map.get(student_id) or {}
        criteria_rows = outcome_criteria.get(outcome.get("name"), {})

        criteria_scores = []
        seen_criteria = set()
        for criterion in criteria_payload:
            criteria_name = criterion.get("assessment_criteria")
            if not criteria_name:
                continue
            seen_criteria.add(criteria_name)
            row = criteria_rows.get(criteria_name) or {}
            criteria_scores.append(
                {
                    "assessment_criteria": criteria_name,
                    "level": row.get("level"),
                    "level_points": _coerce_float(row.get("level_points")),
                    "feedback": row.get("feedback"),
                }
            )

        for criteria_name, row in criteria_rows.items():
            if criteria_name in seen_criteria:
                continue
            criteria_scores.append(
                {
                    "assessment_criteria": criteria_name,
                    "level": row.get("level"),
                    "level_points": _coerce_float(row.get("level_points")),
                    "feedback": row.get("feedback"),
                }
            )

        students_payload.append(
            {
                "task_student": outcome.get("name"),  # compatibility key, points to Task Outcome
                "student": student_id,
                "student_name": (
                    meta.get("student_preferred_name")
                    or meta.get("student_full_name")
                    or student_display_map.get(student_id)
                    or student_id
                ),
                "student_id": meta.get("student_id"),
                "student_image": meta.get("student_image"),
                "status": outcome.get("grading_status"),
                "complete": int(outcome.get("is_complete") or 0),
                "mark_awarded": _coerce_float(outcome.get("official_score")),
                "feedback": outcome.get("official_feedback"),
                "visible_to_student": int(outcome.get("is_published") or 0),
                "visible_to_guardian": int(outcome.get("is_published") or 0),
                "updated_on": outcome.get("modified"),
                "criteria_scores": criteria_scores,
            }
        )

    grading_mode = (delivery.get("grading_mode") or "").strip()
    delivery_mode = (delivery.get("delivery_mode") or "").strip()
    task_payload = {
        "name": delivery.get("name"),
        "title": task_row.get("title") or task_row.get("name"),
        "student_group": delivery.get("student_group"),
        "due_date": delivery.get("due_date"),
        "grading_mode": grading_mode or None,
        "allow_feedback": 1 if _bool_flag(delivery.get("allow_feedback")) else 0,
        "rubric_scoring_strategy": delivery.get("rubric_scoring_strategy") or None,
        "points": 1 if grading_mode == "Points" else 0,
        "binary": 1 if grading_mode in {"Binary", "Completion"} else 0,
        "criteria": 1 if grading_mode == "Criteria" else 0,
        "observations": 1 if delivery_mode in {"Assign Only", "Collect Work"} else 0,
        "max_points": _coerce_float(delivery.get("max_points")),
        "task_type": task_row.get("task_type"),
        "delivery_type": delivery_mode or None,
    }

    return {
        "task": task_payload,
        "criteria": criteria_payload,
        "students": students_payload,
    }


@frappe.whitelist()
def repair_task_roster(task: str):
    """
    Backfill missing Task Outcome rows for a delivery already visible in gradebook.
    """
    if not _can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    _require(task, "Task Delivery")

    delivery = frappe.get_doc("Task Delivery", task)
    _assert_group_access(delivery.student_group)

    before_count = frappe.db.count("Task Outcome", {"task_delivery": delivery.name})
    was_draft = int(delivery.docstatus or 0) == 0

    if was_draft:
        delivery.flags.ignore_permissions = True
        delivery.submit()
        delivery = frappe.get_doc("Task Delivery", task)

    materialized = delivery.materialize_roster()
    after_count = frappe.db.count("Task Outcome", {"task_delivery": delivery.name})
    outcomes_created = max(after_count - before_count, 0)
    eligible_students = materialized.get("eligible_students", after_count)

    if outcomes_created:
        message = _("Roster synced for {student_count} students.").format(student_count=outcomes_created)
    elif after_count:
        message = _("Roster is already up to date.")
    else:
        message = _("No active students are currently in this student group.")

    return {
        "task_delivery": delivery.name,
        "docstatus": int(delivery.docstatus or 0),
        "was_draft": 1 if was_draft else 0,
        "eligible_students": eligible_students,
        "outcomes_created": outcomes_created,
        "outcomes_total": after_count,
        "message": message,
    }


@frappe.whitelist()
def update_task_student(task_student: str, updates=None, **kwargs):
    """
    Update gradebook row for a Task Outcome id.
    Writes run through contribution services for grading data.
    """
    if not _can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    _require(task_student, "Task Outcome")

    payload = updates if updates is not None else kwargs
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("Updates payload must be a dict."))

    outcome_row = frappe.db.get_value(
        "Task Outcome",
        task_student,
        ["name", "task_delivery", "official_score"],
        as_dict=True,
    )
    if not outcome_row:
        frappe.throw(_("Task Outcome not found."))

    delivery_row = (
        frappe.db.get_value(
            "Task Delivery",
            outcome_row.get("task_delivery"),
            ["name", "student_group", "delivery_mode", "grading_mode", "allow_feedback"],
            as_dict=True,
        )
        or {}
    )
    _assert_group_access(delivery_row.get("student_group"))

    grading_mode = (delivery_row.get("grading_mode") or "").strip()
    delivery_mode = (delivery_row.get("delivery_mode") or "").strip()
    allow_feedback = _bool_flag(delivery_row.get("allow_feedback"))
    boolean_mode = grading_mode in {"Binary", "Completion"} or delivery_mode == "Assign Only"
    score_provided = "mark_awarded" in payload and payload.get("mark_awarded") not in (None, "")
    feedback_provided = "feedback" in payload
    criteria_provided = isinstance(payload.get("criteria_scores"), list)
    complete_provided = "complete" in payload

    if score_provided and grading_mode != "Points":
        frappe.throw(_("Points can only be recorded for points grading."))

    if criteria_provided and grading_mode != "Criteria":
        frappe.throw(_("Criteria scores can only be recorded for criteria grading."))

    if complete_provided and not boolean_mode:
        frappe.throw(_("Completion can only be recorded for completion, binary, or assign-only work."))

    if feedback_provided and not allow_feedback:
        frappe.throw(_("Comments are not enabled for this delivery."))

    if score_provided or feedback_provided or criteria_provided:
        contribution_payload = {"task_outcome": task_student}
        if score_provided:
            contribution_payload["score"] = payload.get("mark_awarded")
        elif grading_mode == "Points" and outcome_row.get("official_score") not in (None, ""):
            contribution_payload["score"] = outcome_row.get("official_score")

        if feedback_provided:
            contribution_payload["feedback"] = payload.get("feedback")

        if criteria_provided:
            rubric_scores = []
            for row in payload.get("criteria_scores") or []:
                if not isinstance(row, dict):
                    continue
                criteria_name = row.get("assessment_criteria")
                level_value = row.get("level")
                if not criteria_name or level_value in (None, ""):
                    continue
                rubric_scores.append(
                    {
                        "assessment_criteria": criteria_name,
                        "level": level_value,
                        "level_points": _coerce_float(row.get("level_points")),
                        "feedback": row.get("feedback"),
                    }
                )
            if rubric_scores:
                contribution_payload["rubric_scores"] = rubric_scores

        should_submit_contribution = True
        if grading_mode == "Criteria" and not contribution_payload.get("rubric_scores"):
            existing_scores = _build_rubric_scores_from_outcome(task_student)
            if existing_scores:
                contribution_payload["rubric_scores"] = existing_scores
            elif criteria_provided:
                frappe.throw(_("Criteria levels are required before saving criteria marks."))
            elif not feedback_provided:
                should_submit_contribution = False

        if should_submit_contribution:
            _reject_official_fields(contribution_payload)
            contribution_payload["task_submission"] = _resolve_or_create_stub_submission_id(
                task_student, contribution_payload
            )
            task_contribution_service.submit_contribution(contribution_payload, contributor=frappe.session.user)

    status_value = _normalize_grading_status(payload.get("status")) if "status" in payload else None
    visibility_provided = "visible_to_student" in payload or "visible_to_guardian" in payload
    if status_value is not None and delivery_mode != "Assess":
        frappe.throw(_("Grading status can only be updated for assessed work."))
    if status_value is not None or complete_provided or visibility_provided:
        outcome_doc = frappe.get_doc("Task Outcome", task_student)
        if status_value is not None:
            outcome_doc.grading_status = status_value
        if complete_provided:
            outcome_doc.is_complete = 1 if _bool_flag(payload.get("complete")) else 0
        if visibility_provided:
            publish_flag = _bool_flag(payload.get("visible_to_student")) or _bool_flag(
                payload.get("visible_to_guardian")
            )
            outcome_doc.is_published = 1 if publish_flag else 0
            if publish_flag:
                outcome_doc.published_on = now_datetime()
                outcome_doc.published_by = frappe.session.user
            else:
                outcome_doc.published_on = None
                outcome_doc.published_by = None
        outcome_doc.save(ignore_permissions=False)

    fresh = (
        frappe.db.get_value(
            "Task Outcome",
            task_student,
            [
                "name",
                "official_score",
                "official_feedback",
                "grading_status",
                "is_complete",
                "is_published",
                "modified",
            ],
            as_dict=True,
        )
        or {}
    )
    return {
        "task_student": fresh.get("name"),
        "mark_awarded": _coerce_float(fresh.get("official_score")),
        "feedback": fresh.get("official_feedback"),
        "status": fresh.get("grading_status"),
        "complete": int(fresh.get("is_complete") or 0),
        "visible_to_student": int(fresh.get("is_published") or 0),
        "visible_to_guardian": int(fresh.get("is_published") or 0),
        "updated_on": fresh.get("modified"),
    }


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
        limit=0,
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

    employee = frappe.db.get_value("Employee", {"user_id": user, "employment_status": "Active"}, "name")
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
        limit=0,
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
        limit=0,
    )
    criteria_map = {}
    for row in rows:
        parent = row.get("parent")
        if not parent:
            continue
        criteria_map.setdefault(parent, []).append(
            {
                "criteria": row.get("assessment_criteria"),
                "level": row.get("level"),
                "points": row.get("level_points"),
            }
        )
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
        limit=0,
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
        history.append(
            {
                "by": row.get("contributor") or "Moderator",
                "action": row.get("moderation_action"),
                "on": row.get("submitted_on") or row.get("modified"),
            }
        )
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
        limit=0,
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
        limit=1,
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


def _assert_group_access(student_group):
    if not student_group:
        return
    if not _is_instructor_scoped_user():
        return
    names = _instructor_group_names(frappe.session.user)
    if student_group not in names:
        frappe.throw(_("You do not have access to this student group."), frappe.PermissionError)


def _resolve_delivery(delivery_id):
    delivery = frappe.db.get_value(
        "Task Delivery",
        delivery_id,
        [
            "name",
            "task",
            "student_group",
            "due_date",
            "delivery_mode",
            "grading_mode",
            "allow_feedback",
            "max_points",
            "rubric_version",
            "rubric_scoring_strategy",
        ],
        as_dict=True,
    )
    if not delivery:
        frappe.throw(_("Task Delivery not found."))
    return delivery


def _build_delivery_criteria_payload(delivery):
    if not delivery:
        return []

    grading_mode = (delivery.get("grading_mode") or "").strip()
    if grading_mode != "Criteria":
        return []

    rubric_version = delivery.get("rubric_version")
    if not rubric_version:
        return []

    rows = frappe.get_all(
        "Task Rubric Criterion",
        filters={
            "parent": rubric_version,
            "parenttype": "Task Rubric Version",
            "parentfield": "criteria",
        },
        fields=["assessment_criteria", "criteria_name", "criteria_weighting"],
        order_by="idx asc",
        limit=0,
    )
    criteria_ids = [row.get("assessment_criteria") for row in rows if row.get("assessment_criteria")]
    levels_map = _get_assessment_levels_map(criteria_ids)

    out = []
    for row in rows:
        criteria_name = row.get("assessment_criteria")
        if not criteria_name:
            continue
        out.append(
            {
                "assessment_criteria": criteria_name,
                "criteria_name": row.get("criteria_name") or criteria_name,
                "criteria_weighting": _coerce_float(row.get("criteria_weighting")),
                "levels": levels_map.get(criteria_name, []),
            }
        )
    return out


def _get_assessment_levels_map(criteria_ids):
    ids = [criteria_id for criteria_id in dict.fromkeys(criteria_ids or []) if criteria_id]
    if not ids:
        return {}

    rows = frappe.get_all(
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
    levels = {}
    for row in rows:
        parent = row.get("parent")
        level = row.get("achievement_level")
        if not parent or not level:
            continue
        levels.setdefault(parent, []).append({"level": level, "points": 0})
    return levels


def _get_outcome_criteria_rows(outcome_ids):
    ids = [outcome_id for outcome_id in dict.fromkeys(outcome_ids or []) if outcome_id]
    if not ids:
        return {}

    rows = frappe.get_all(
        "Task Outcome Criterion",
        filters={
            "parent": ["in", ids],
            "parenttype": "Task Outcome",
            "parentfield": "official_criteria",
        },
        fields=["parent", "assessment_criteria", "level", "level_points", "feedback"],
        order_by="idx asc",
        limit=0,
    )
    out = {}
    for row in rows:
        parent = row.get("parent")
        criteria_name = row.get("assessment_criteria")
        if not parent or not criteria_name:
            continue
        out.setdefault(parent, {})[criteria_name] = {
            "level": row.get("level"),
            "level_points": row.get("level_points"),
            "feedback": row.get("feedback"),
        }
    return out


def _get_student_meta_map(student_ids):
    ids = [student_id for student_id in dict.fromkeys(student_ids or []) if student_id]
    if not ids:
        return {}

    meta = frappe.get_meta("Student")
    fields = ["name"]
    for fieldname in ("student_preferred_name", "student_full_name", "student_id", "student_image"):
        if meta.get_field(fieldname):
            fields.append(fieldname)

    rows = frappe.get_all(
        "Student",
        filters={"name": ["in", ids]},
        fields=fields,
        limit=0,
    )
    apply_preferred_student_images(rows, student_field="name", image_field="student_image")
    return {row.get("name"): row for row in rows if row.get("name")}


def _build_rubric_scores_from_outcome(outcome_id):
    rows = frappe.get_all(
        "Task Outcome Criterion",
        filters={
            "parent": outcome_id,
            "parenttype": "Task Outcome",
            "parentfield": "official_criteria",
        },
        fields=["assessment_criteria", "level", "level_points", "feedback"],
        order_by="idx asc",
        limit=0,
    )
    scores = []
    for row in rows:
        criteria_name = row.get("assessment_criteria")
        level_value = row.get("level")
        if not criteria_name or level_value in (None, ""):
            continue
        scores.append(
            {
                "assessment_criteria": criteria_name,
                "level": level_value,
                "level_points": _coerce_float(row.get("level_points")),
                "feedback": row.get("feedback"),
            }
        )
    return scores


def _normalize_grading_status(value):
    if value in (None, ""):
        return None
    allowed = {
        "Not Applicable",
        "Not Started",
        "In Progress",
        "Needs Review",
        "Moderated",
        "Finalized",
        "Released",
    }
    text = str(value).strip()
    if text in allowed:
        return text
    return None


def _coerce_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None
