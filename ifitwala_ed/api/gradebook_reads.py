# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _


def get_grid(api, filters=None, **kwargs):
    if not api._can_read_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_filters(filters, kwargs)
    school = data.get("school")
    academic_year = data.get("academic_year")
    course = data.get("course")
    student_group = data.get("student_group")
    task_type = data.get("task_type")
    delivery_mode = data.get("delivery_mode")
    assessment_scope = str(data.get("assessment_scope") or "").strip().lower()
    api._require(school, "School")
    api._require(academic_year, "Academic Year")

    scope = api._resolve_gradebook_scope(school, academic_year, course)
    delivery_filters = {
        "school": school,
        "academic_year": academic_year,
    }
    if student_group:
        api._assert_group_access(student_group)
        delivery_filters["student_group"] = student_group
    elif scope.get("student_groups"):
        delivery_filters["student_group"] = ["in", scope["student_groups"]]
    if scope.get("courses"):
        delivery_filters["course"] = ["in", scope["courses"]]
    if delivery_mode:
        delivery_filters["delivery_mode"] = delivery_mode
    elif assessment_scope == "graded":
        delivery_filters["delivery_mode"] = "Assess"
    elif assessment_scope == "not_graded":
        delivery_filters["delivery_mode"] = ["in", ["Collect Work", "Assign Only"]]
    elif assessment_scope and assessment_scope != "all":
        frappe.throw(_("Assessment scope must be graded, not_graded, or all."))

    limit = api._coerce_int(data.get("limit"), default=12, minimum=1, maximum=20)

    deliveries = frappe.get_all(
        "Task Delivery",
        filters=delivery_filters,
        fields=[
            "name",
            "task",
            "grading_mode",
            "rubric_scoring_strategy",
            "due_date",
            "delivery_mode",
            "allow_feedback",
            "max_points",
        ],
        order_by="due_date desc, name desc",
        limit=0,
    )
    if not deliveries:
        return {"deliveries": [], "students": [], "cells": []}

    task_map = api._get_task_summary_map([row.get("task") for row in deliveries])
    if task_type:
        deliveries = [row for row in deliveries if (task_map.get(row.get("task")) or {}).get("task_type") == task_type]
        if not deliveries:
            return {"deliveries": [], "students": [], "cells": []}

    deliveries = sorted(
        deliveries[:limit],
        key=lambda row: (
            row.get("due_date") or "",
            row.get("name") or "",
        ),
    )
    delivery_map = {row["name"]: row for row in deliveries}

    delivery_payload = []
    for row in deliveries:
        task_row = task_map.get(row.get("task")) or {}
        delivery_payload.append(
            {
                "delivery_id": row.get("name"),
                "task_title": task_row.get("title") or row.get("task"),
                "grading_mode": row.get("grading_mode"),
                "rubric_scoring_strategy": row.get("rubric_scoring_strategy"),
                "due_date": row.get("due_date"),
                "delivery_mode": row.get("delivery_mode"),
                "allow_feedback": 1 if api._bool_flag(row.get("allow_feedback")) else 0,
                "max_points": api._coerce_float(row.get("max_points")),
                "task_type": task_row.get("task_type"),
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
            "official_feedback",
            "is_complete",
            "is_published",
        ],
        order_by="student asc, task_delivery asc",
        limit=0,
    )

    student_ids = [row.get("student") for row in outcomes if row.get("student")]
    student_map = api._get_student_display_map(student_ids)
    student_meta_map = api._get_student_meta_map(student_ids)
    students = api._build_student_payload(student_ids, student_map, student_meta_map)

    criteria_outcome_ids = {
        row.get("name")
        for row in outcomes
        if delivery_map.get(row.get("task_delivery"), {}).get("grading_mode") == "Criteria"
    }
    criteria_map = api._get_outcome_criteria_map(criteria_outcome_ids)

    cells = []
    for row in outcomes:
        outcome_id = row.get("name")
        delivery_id = row.get("task_delivery")
        delivery = delivery_map.get(delivery_id, {})
        cell = {
            "outcome_id": outcome_id,
            "student": row.get("student"),
            "delivery_id": delivery_id,
            "flags": {
                "has_submission": api._bool_flag(row.get("has_submission")),
                "has_new_submission": api._bool_flag(row.get("has_new_submission")),
                "grading_status": row.get("grading_status"),
                "procedural_status": row.get("procedural_status"),
                "is_complete": api._bool_flag(row.get("is_complete")),
                "is_published": api._bool_flag(row.get("is_published")),
            },
            "official": {
                "score": row.get("official_score"),
                "grade": row.get("official_grade"),
                "grade_value": _grade_value_for_payload(row.get("official_grade"), row.get("official_grade_value")),
                "feedback": row.get("official_feedback"),
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


def get_drawer(api, outcome_id: str, submission_id: str | None = None, version: int | str | None = None):
    from ifitwala_ed.api import task_submission as task_submission_api
    from ifitwala_ed.assessment import (
        task_feedback_artifact_service,
        task_feedback_comment_bank_service,
        task_feedback_service,
        task_feedback_thread_service,
    )

    api._require(outcome_id, "Task Outcome")

    if not api._can_read_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    outcome_fields = [
        "name",
        "task_delivery",
        "student",
        "grading_status",
        "procedural_status",
        "has_submission",
        "has_new_submission",
        "is_complete",
        "is_published",
        "published_on",
        "published_by",
        "official_score",
        "official_grade",
        "official_grade_value",
        "official_feedback",
    ]
    outcome_doc = frappe.db.get_value("Task Outcome", outcome_id, outcome_fields, as_dict=True)
    if not outcome_doc:
        frappe.throw(_("Task Outcome not found."))

    delivery = api._resolve_delivery(outcome_doc.get("task_delivery"))
    api._assert_group_access(delivery.get("student_group"))
    task_row = frappe.db.get_value(
        "Task",
        delivery.get("task"),
        ["name", "title", "task_type"],
        as_dict=True,
    ) or {"name": delivery.get("task"), "title": delivery.get("task")}
    delivery_criteria = api._build_delivery_criteria_payload(delivery)

    student_id = outcome_doc.get("student")
    student_meta = api._get_student_meta_map([student_id]).get(student_id, {}) if student_id else {}
    student_display = api._get_student_display_map([student_id]).get(student_id, student_id) if student_id else None

    outcome_criteria = api._get_outcome_criteria_map({outcome_id}).get(outcome_id, [])

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
            "judgment_code",
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
    contributions = [_normalize_contribution_grade_value(row, api) for row in contributions]

    my_contribution = api._select_my_contribution(contributions)
    my_criteria = []
    if my_contribution:
        my_criteria = api._get_contribution_criteria(my_contribution.get("name"))

    moderation_history = api._build_moderation_history(contributions)
    selected_submission_row = task_submission_api.select_task_submission_row(
        submissions,
        submission_id=submission_id,
        version=version,
    )
    latest_submission = submissions[0] if submissions else None
    selected_submission = None
    if selected_submission_row:
        selected_submission = task_submission_api.serialize_task_submission_evidence(
            selected_submission_row,
            is_latest_version=bool(
                latest_submission and selected_submission_row.get("name") == latest_submission.get("name")
            ),
        )
    selected_submission_id = (selected_submission or {}).get("submission_id")
    feedback_workspace = None
    if selected_submission_id:
        feedback_workspace = task_feedback_service.build_feedback_workspace_payload(
            outcome_id,
            selected_submission_id,
        )
    feedback_threads = []
    if selected_submission_id:
        feedback_threads = task_feedback_thread_service.build_feedback_thread_payloads(
            outcome_id=outcome_id,
            submission_id=selected_submission_id,
        )
    feedback_artifact = None
    if selected_submission_id:
        feedback_artifact = task_feedback_artifact_service.get_current_released_feedback_pdf_artifact(
            outcome_id,
            audience="student",
            submission_id=selected_submission_id,
        )
    comment_bank = task_feedback_comment_bank_service.build_comment_bank_payload(
        outcome_id,
        actor=frappe.session.user,
    )
    submission_versions = [
        task_submission_api.build_task_submission_version_summary(
            row,
            is_selected=(row.get("name") == selected_submission_id),
        )
        for row in sorted(submissions, key=lambda r: r.get("version") or 0)
    ]
    if latest_submission:
        latest_submission = task_submission_api.build_task_submission_version_summary(
            latest_submission,
            is_selected=(latest_submission.get("name") == selected_submission_id),
        )

    return {
        "delivery": {
            "name": delivery.get("name"),
            "task": task_row.get("name"),
            "title": task_row.get("title") or task_row.get("name"),
            "task_type": task_row.get("task_type"),
            "student_group": delivery.get("student_group"),
            "due_date": delivery.get("due_date"),
            "delivery_mode": delivery.get("delivery_mode"),
            "grading_mode": delivery.get("grading_mode"),
            "allow_feedback": 1 if api._bool_flag(delivery.get("allow_feedback")) else 0,
            "rubric_scoring_strategy": delivery.get("rubric_scoring_strategy") or None,
            "max_points": api._coerce_float(delivery.get("max_points")),
            "criteria": delivery_criteria,
        },
        "student": {
            "student": student_id,
            "student_name": student_meta.get("student_preferred_name")
            or student_meta.get("student_full_name")
            or student_display
            or student_id,
            "student_id": student_meta.get("student_id"),
            "student_image": student_meta.get("student_image"),
        },
        "outcome": {
            "outcome_id": outcome_doc.get("name"),
            "grading_status": outcome_doc.get("grading_status"),
            "procedural_status": outcome_doc.get("procedural_status"),
            "has_submission": api._bool_flag(outcome_doc.get("has_submission")),
            "has_new_submission": api._bool_flag(outcome_doc.get("has_new_submission")),
            "is_complete": api._bool_flag(outcome_doc.get("is_complete")),
            "is_published": api._bool_flag(outcome_doc.get("is_published")),
            "published_on": outcome_doc.get("published_on"),
            "published_by": outcome_doc.get("published_by"),
            "official": {
                "score": outcome_doc.get("official_score"),
                "grade": outcome_doc.get("official_grade"),
                "grade_value": _grade_value_for_payload(
                    outcome_doc.get("official_grade"),
                    outcome_doc.get("official_grade_value"),
                ),
                "feedback": outcome_doc.get("official_feedback"),
            },
            "criteria": outcome_criteria,
        },
        "latest_submission": latest_submission,
        "selected_submission": selected_submission,
        "feedback_workspace": feedback_workspace,
        "feedback_artifact": feedback_artifact,
        "feedback_threads": feedback_threads,
        "comment_bank": comment_bank,
        "submission_versions": submission_versions,
        "my_contribution": {
            "name": my_contribution.get("name"),
            "status": my_contribution.get("status"),
            "contribution_type": my_contribution.get("contribution_type"),
            "task_submission": my_contribution.get("task_submission"),
            "is_stale": api._bool_flag(my_contribution.get("is_stale")),
            "judgment_code": my_contribution.get("judgment_code"),
            "score": api._coerce_float(my_contribution.get("score")),
            "grade": my_contribution.get("grade"),
            "grade_value": _grade_value_for_payload(
                my_contribution.get("grade"),
                api._coerce_float(my_contribution.get("grade_value")),
            ),
            "criteria": my_criteria,
            "feedback": my_contribution.get("feedback"),
            "submitted_on": my_contribution.get("submitted_on"),
            "modified": my_contribution.get("modified"),
        }
        if my_contribution
        else None,
        "moderation_history": moderation_history,
        "allowed_actions": {
            "can_edit_marking": api._can_write_gradebook(),
            "can_edit_feedback": api._can_write_gradebook(),
            "can_mark_submission_seen": api._can_write_gradebook() or api._is_academic_adminish(),
            "can_publish": api._can_write_gradebook() or api._is_academic_adminish(),
            "can_unpublish": api._is_academic_adminish(),
            "can_manage_feedback_publication": api._can_write_gradebook() or api._is_academic_adminish(),
            "can_moderate": api._is_academic_adminish(),
            "show_review_tab": api._is_academic_adminish(),
        },
        "contributions": contributions,
    }


def _grade_value_for_payload(grade_symbol, grade_value):
    if grade_symbol in (None, ""):
        return None
    if not str(grade_symbol).strip():
        return None
    return grade_value


def _normalize_contribution_grade_value(row, api):
    if not isinstance(row, dict):
        return row

    normalized = dict(row)
    normalized["grade_value"] = _grade_value_for_payload(
        normalized.get("grade"),
        api._coerce_float(normalized.get("grade_value")),
    )
    return normalized


def fetch_groups(api, search=None, limit=None, school=None, academic_year=None, program=None, course=None):
    if not api._can_read_gradebook():
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

    if api._is_instructor_scoped_user():
        names = sorted(api._instructor_group_names(frappe.session.user))
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


def fetch_group_tasks(api, student_group: str):
    if not api._can_read_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    api._require(student_group, "Student Group")
    api._assert_group_access(student_group)

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
                "name": delivery.get("name"),
                "title": task_row.get("title") or delivery.get("task"),
                "due_date": delivery.get("due_date"),
                "status": None,
                "grading_mode": grading_mode or None,
                "allow_feedback": 1 if api._bool_flag(delivery.get("allow_feedback")) else 0,
                "rubric_scoring_strategy": delivery.get("rubric_scoring_strategy") or None,
                "points": 1 if grading_mode == "Points" else 0,
                "binary": 1 if grading_mode in {"Binary", "Completion"} else 0,
                "criteria": 1 if grading_mode == "Criteria" else 0,
                "observations": 1 if delivery_mode in {"Assign Only", "Collect Work"} else 0,
                "max_points": api._coerce_float(delivery.get("max_points")),
                "task_type": task_row.get("task_type"),
                "delivery_type": delivery_mode or None,
            }
        )

    return {"tasks": tasks}


def get_task_gradebook(api, task: str):
    if not api._can_read_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    api._require(task, "Task Delivery")

    delivery = api._resolve_delivery(task)
    api._assert_group_access(delivery.get("student_group"))

    task_row = frappe.db.get_value(
        "Task",
        delivery.get("task"),
        ["name", "title", "task_type"],
        as_dict=True,
    ) or {"name": delivery.get("task"), "title": delivery.get("task")}

    criteria_payload = api._build_delivery_criteria_payload(delivery)

    outcomes = frappe.get_all(
        "Task Outcome",
        filters={"task_delivery": delivery.get("name")},
        fields=[
            "name",
            "student",
            "grading_status",
            "procedural_status",
            "submission_status",
            "has_submission",
            "has_new_submission",
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
    outcome_criteria = api._get_outcome_criteria_rows(outcome_ids)

    student_ids = [row.get("student") for row in outcomes if row.get("student")]
    student_display_map = api._get_student_display_map(student_ids)
    student_meta_map = api._get_student_meta_map(student_ids)

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
                    "level_points": api._coerce_float(row.get("level_points")),
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
                    "level_points": api._coerce_float(row.get("level_points")),
                    "feedback": row.get("feedback"),
                }
            )

        students_payload.append(
            {
                "task_student": outcome.get("name"),
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
                "procedural_status": outcome.get("procedural_status"),
                "submission_status": outcome.get("submission_status"),
                "has_submission": int(outcome.get("has_submission") or 0),
                "has_new_submission": int(outcome.get("has_new_submission") or 0),
                "complete": int(outcome.get("is_complete") or 0),
                "mark_awarded": api._coerce_float(outcome.get("official_score")),
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
        "allow_feedback": 1 if api._bool_flag(delivery.get("allow_feedback")) else 0,
        "rubric_scoring_strategy": delivery.get("rubric_scoring_strategy") or None,
        "points": 1 if grading_mode == "Points" else 0,
        "binary": 1 if grading_mode in {"Binary", "Completion"} else 0,
        "criteria": 1 if grading_mode == "Criteria" else 0,
        "observations": 1 if delivery_mode in {"Assign Only", "Collect Work"} else 0,
        "max_points": api._coerce_float(delivery.get("max_points")),
        "task_type": task_row.get("task_type"),
        "delivery_type": delivery_mode or None,
    }

    return {
        "task": task_payload,
        "criteria": criteria_payload,
        "students": students_payload,
    }


def get_task_quiz_manual_review(
    api, task: str, view_mode: str | None = None, quiz_question: str | None = None, student: str | None = None
):
    if not api._can_read_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    api._require(task, "Task Delivery")

    delivery = api._resolve_delivery(task)
    api._assert_group_access(delivery.get("student_group"))
    task_row = api._require_manual_quiz_review_delivery(delivery)
    review_rows = api._build_quiz_manual_review_rows(delivery)
    mode = api._normalize_quiz_manual_view_mode(view_mode)

    question_options = api._build_quiz_manual_question_options(review_rows)
    student_options = api._build_quiz_manual_student_options(review_rows)

    selected_question = None
    selected_student = None
    filtered_rows = review_rows

    if mode == "question":
        selected_question = api._resolve_selected_quiz_manual_question(quiz_question, question_options)
        filtered_rows = (
            [row for row in review_rows if row.get("quiz_question") == selected_question] if selected_question else []
        )
    else:
        selected_student = api._resolve_selected_quiz_manual_student(student, student_options)
        filtered_rows = (
            [row for row in review_rows if row.get("student") == selected_student] if selected_student else []
        )

    return {
        "task": {
            "name": delivery.get("name"),
            "title": task_row.get("title") or task_row.get("name"),
            "student_group": delivery.get("student_group"),
            "max_points": api._coerce_float(delivery.get("max_points")),
            "pass_percentage": api._coerce_float(delivery.get("quiz_pass_percentage")),
        },
        "summary": {
            "manual_item_count": len(review_rows),
            "pending_item_count": sum(1 for row in review_rows if int(row.get("requires_manual_grading") or 0) == 1),
            "pending_student_count": len(
                {
                    row.get("student")
                    for row in review_rows
                    if int(row.get("requires_manual_grading") or 0) == 1 and row.get("student")
                }
            ),
            "pending_attempt_count": len(
                {
                    row.get("quiz_attempt")
                    for row in review_rows
                    if int(row.get("requires_manual_grading") or 0) == 1 and row.get("quiz_attempt")
                }
            ),
        },
        "view_mode": mode,
        "questions": question_options,
        "students": student_options,
        "selected_question": (
            next(
                (
                    {
                        "quiz_question": row.get("quiz_question"),
                        "title": row.get("title"),
                    }
                    for row in question_options
                    if row.get("quiz_question") == selected_question
                ),
                None,
            )
            if selected_question
            else None
        ),
        "selected_student": (
            next(
                (
                    {
                        "student": row.get("student"),
                        "student_name": row.get("student_name"),
                        "student_id": row.get("student_id"),
                    }
                    for row in student_options
                    if row.get("student") == selected_student
                ),
                None,
            )
            if selected_student
            else None
        ),
        "rows": filtered_rows,
    }
