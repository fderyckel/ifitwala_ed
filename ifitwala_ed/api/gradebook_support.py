# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
from frappe import _

from ifitwala_ed.assessment import quiz_service, task_submission_service
from ifitwala_ed.utilities.image_utils import apply_preferred_student_images


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


def _normalize_quiz_manual_view_mode(value: str | None) -> str:
    return "student" if str(value or "").strip() == "student" else "question"


def _require_manual_quiz_review_delivery(delivery):
    task_name = delivery.get("task")
    task_row = frappe.db.get_value(
        "Task",
        task_name,
        ["name", "title", "task_type"],
        as_dict=True,
    )
    if not task_row:
        frappe.throw(_("Task not found."))
    if (task_row.get("task_type") or "").strip() != "Quiz":
        frappe.throw(_("Quiz manual review is only available for quiz deliveries."))
    if (delivery.get("delivery_mode") or "").strip() != "Assess":
        frappe.throw(_("Quiz manual review is only available for assessed quiz deliveries."))
    return task_row


def _build_quiz_manual_review_rows(delivery):
    outcome_rows = frappe.get_all(
        "Task Outcome",
        filters={"task_delivery": delivery.get("name")},
        fields=["name", "student", "grading_status"],
        limit=0,
    )
    outcome_map = {row.get("name"): row for row in outcome_rows if row.get("name")}

    attempt_rows = frappe.get_all(
        "Quiz Attempt",
        filters={
            "task_delivery": delivery.get("name"),
            "status": ["in", ["Submitted", "Needs Review"]],
        },
        fields=[
            "name",
            "task_outcome",
            "student",
            "attempt_number",
            "status",
            "submitted_on",
            "score",
            "percentage",
            "passed",
            "requires_manual_review",
        ],
        order_by="submitted_on desc, attempt_number desc, name asc",
        limit=0,
    )
    attempt_map = {row.get("name"): row for row in attempt_rows if row.get("name")}
    if not attempt_map:
        return []

    item_rows = frappe.get_all(
        "Quiz Attempt Item",
        filters={
            "quiz_attempt": ["in", list(attempt_map.keys())],
            "question_type": ["in", sorted(quiz_service.MANUAL_TYPES)],
        },
        fields=[
            "name",
            "quiz_attempt",
            "quiz_question",
            "position",
            "question_type",
            "prompt_html",
            "option_payload",
            "response_text",
            "response_payload",
            "awarded_score",
            "requires_manual_grading",
        ],
        order_by="position asc, name asc",
        limit=0,
    )
    if not item_rows:
        return []

    question_rows = frappe.get_all(
        "Quiz Question",
        filters={"name": ["in", list({row.get("quiz_question") for row in item_rows if row.get("quiz_question")})]},
        fields=["name", "title"],
        limit=0,
    )
    question_map = {row.get("name"): row for row in question_rows if row.get("name")}

    student_ids = []
    for attempt in attempt_rows:
        student_id = attempt.get("student") or outcome_map.get(attempt.get("task_outcome"), {}).get("student")
        if student_id:
            student_ids.append(student_id)
    student_display_map = _get_student_display_map(student_ids)
    student_meta_map = _get_student_meta_map(student_ids)

    rows = []
    for item in item_rows:
        attempt = attempt_map.get(item.get("quiz_attempt"))
        if not attempt:
            continue
        outcome = outcome_map.get(attempt.get("task_outcome")) or {}
        student_id = attempt.get("student") or outcome.get("student")
        if not student_id:
            continue
        question = question_map.get(item.get("quiz_question")) or {}
        student_meta = student_meta_map.get(student_id) or {}
        selected_option_ids = _parse_quiz_manual_response_ids(item.get("response_payload"))
        rows.append(
            {
                "item_id": item.get("name"),
                "quiz_attempt": attempt.get("name"),
                "task_outcome": attempt.get("task_outcome"),
                "attempt_number": attempt.get("attempt_number"),
                "attempt_status": attempt.get("status"),
                "submitted_on": attempt.get("submitted_on"),
                "student": student_id,
                "student_name": student_display_map.get(student_id) or student_id,
                "student_id": student_meta.get("student_id"),
                "student_image": student_meta.get("student_image"),
                "grading_status": outcome.get("grading_status"),
                "quiz_question": item.get("quiz_question"),
                "title": question.get("title") or item.get("quiz_question"),
                "position": item.get("position"),
                "question_type": item.get("question_type"),
                "prompt_html": item.get("prompt_html"),
                "response_text": item.get("response_text"),
                "selected_option_ids": selected_option_ids,
                "selected_option_labels": _resolve_quiz_manual_selected_option_labels(
                    item.get("option_payload"), selected_option_ids
                ),
                "awarded_score": _coerce_float(item.get("awarded_score")),
                "requires_manual_grading": 1 if _bool_flag(item.get("requires_manual_grading")) else 0,
            }
        )

    rows.sort(
        key=lambda row: (
            str(row.get("title") or "").lower(),
            str(row.get("student_name") or "").lower(),
            row.get("attempt_number") or 0,
            row.get("position") or 0,
            str(row.get("item_id") or ""),
        )
    )
    return rows


def _build_quiz_manual_question_options(rows):
    options = {}
    for row in rows:
        quiz_question = row.get("quiz_question")
        if not quiz_question:
            continue
        option = options.setdefault(
            quiz_question,
            {
                "quiz_question": quiz_question,
                "title": row.get("title") or quiz_question,
                "manual_item_count": 0,
                "pending_item_count": 0,
            },
        )
        option["manual_item_count"] += 1
        if int(row.get("requires_manual_grading") or 0) == 1:
            option["pending_item_count"] += 1

    return sorted(
        options.values(),
        key=lambda row: (str(row.get("title") or "").lower(), str(row.get("quiz_question") or "")),
    )


def _build_quiz_manual_student_options(rows):
    options = {}
    for row in rows:
        student = row.get("student")
        if not student:
            continue
        option = options.setdefault(
            student,
            {
                "student": student,
                "student_name": row.get("student_name") or student,
                "student_id": row.get("student_id"),
                "student_image": row.get("student_image"),
                "manual_item_count": 0,
                "pending_item_count": 0,
            },
        )
        option["manual_item_count"] += 1
        if int(row.get("requires_manual_grading") or 0) == 1:
            option["pending_item_count"] += 1

    return sorted(
        options.values(),
        key=lambda row: (
            str(row.get("student_name") or "").lower(),
            str(row.get("student_id") or ""),
            str(row.get("student") or ""),
        ),
    )


def _resolve_selected_quiz_manual_question(requested, question_options):
    requested_value = str(requested or "").strip()
    if requested_value and any(row.get("quiz_question") == requested_value for row in question_options):
        return requested_value
    return question_options[0].get("quiz_question") if question_options else None


def _resolve_selected_quiz_manual_student(requested, student_options):
    requested_value = str(requested or "").strip()
    if requested_value and any(row.get("student") == requested_value for row in student_options):
        return requested_value
    return student_options[0].get("student") if student_options else None


def _parse_quiz_manual_response_ids(value) -> list[str]:
    if value in (None, ""):
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(entry).strip() for entry in parsed if str(entry).strip()]


def _resolve_quiz_manual_selected_option_labels(option_payload, selected_option_ids) -> list[str]:
    if not option_payload or not selected_option_ids:
        return []
    try:
        parsed = json.loads(option_payload) if isinstance(option_payload, str) else option_payload
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []

    option_map = {}
    for row in parsed:
        if not isinstance(row, dict):
            continue
        option_id = str(row.get("id") or "").strip()
        if not option_id:
            continue
        option_map[option_id] = str(row.get("text") or "").strip() or option_id

    labels = []
    for option_id in selected_option_ids:
        label = option_map.get(option_id)
        if label:
            labels.append(label)
    return labels


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
    from ifitwala_ed.api.student_groups import _instructor_group_names as _canonical_instructor_group_names

    return _canonical_instructor_group_names(user)


def _get_task_summary_map(task_ids):
    task_ids = [task_id for task_id in set(task_ids or []) if task_id]
    if not task_ids:
        return {}

    rows = frappe.get_all(
        "Task",
        filters={"name": ["in", task_ids]},
        fields=["name", "title", "task_type"],
        limit=0,
    )
    return {row.get("name"): row for row in rows if row.get("name")}


def _build_student_payload(student_ids, student_map, student_meta_map=None):
    unique_ids = {student_id for student_id in student_ids if student_id}
    meta_map = student_meta_map or {}
    ordered = sorted(
        unique_ids,
        key=lambda sid: (
            (student_map.get(sid) or sid).lower(),
            sid,
        ),
    )
    return [
        {
            "student": student_id,
            "student_name": student_map.get(student_id) or student_id,
            "student_id": (meta_map.get(student_id) or {}).get("student_id"),
            "student_image": (meta_map.get(student_id) or {}).get("student_image"),
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
        fields=["assessment_criteria", "level", "level_points", "feedback"],
        order_by="idx asc",
        limit=0,
    )
    return [
        {
            "criteria": row.get("assessment_criteria"),
            "level": row.get("level"),
            "points": row.get("level_points"),
            "feedback": row.get("feedback"),
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
            "quiz_pass_percentage",
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
        fields=["assessment_criteria", "criteria_name", "criteria_weighting", "criteria_max_points"],
        order_by="idx asc",
        limit=0,
    )
    criteria_meta = {
        row.get("assessment_criteria"): {"criteria_max_points": _coerce_float(row.get("criteria_max_points"))}
        for row in rows
        if row.get("assessment_criteria")
    }
    levels_map = _get_assessment_levels_map(criteria_meta)

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
    ids = [criteria_id for criteria_id in dict.fromkeys((criteria_ids or {}).keys()) if criteria_id]
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
        levels.setdefault(parent, []).append(level)
    return {
        criteria_id: _build_level_point_rows(criteria_id, level_rows, criteria_ids)
        for criteria_id, level_rows in levels.items()
    }


def _build_level_point_rows(criteria_id, level_rows, criteria_meta):
    rows = [str(level or "").strip() for level in (level_rows or []) if str(level or "").strip()]
    if not rows:
        return []

    meta = criteria_meta.get(criteria_id) or {}
    max_points = _coerce_float(meta.get("criteria_max_points"))
    numeric_rows = [_parse_numeric_level(level) for level in rows]
    if all(value is not None for value in numeric_rows):
        max_level = max(value for value in numeric_rows if value is not None)
        scale = 1.0
        if max_points is not None and max_points > 0 and max_level > 0:
            scale = max_points / max_level
        return [
            {"level": level, "points": _normalize_derived_points((value or 0) * scale)}
            for level, value in zip(rows, numeric_rows)
        ]

    if max_points is not None and max_points > 0:
        divisor = float(len(rows) or 1)
        return [
            {
                "level": level,
                "points": _normalize_derived_points(max_points * ((index + 1) / divisor)),
            }
            for index, level in enumerate(rows)
        ]

    return [{"level": level, "points": 0} for level in rows]


def _parse_numeric_level(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_derived_points(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    rounded = round(numeric, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return int(round(rounded))
    return rounded


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
    apply_preferred_student_images(
        rows,
        student_field="name",
        image_field="student_image",
        fallback_to_original=False,
    )
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


def _coerce_int(value, default=0, minimum=None, maximum=None):
    try:
        out = int(value)
    except Exception:
        out = default
    if minimum is not None:
        out = max(minimum, out)
    if maximum is not None:
        out = min(maximum, out)
    return out
