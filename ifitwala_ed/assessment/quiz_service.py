# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import hashlib
import json
import random
from datetime import timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from ifitwala_ed.assessment import task_feedback_service, task_outcome_service
from ifitwala_ed.utilities.html_sanitizer import sanitize_html

CHOICE_TYPES = {"Single Choice", "Multiple Answer", "True / False"}
MANUAL_TYPES = {"Essay"}


def open_quiz_session(*, task_delivery: str, student: str, user: str) -> dict[str, Any]:
    delivery = _get_delivery(task_delivery)
    outcome = _get_outcome(task_delivery=task_delivery, student=student)
    current_attempt = _get_latest_in_progress_attempt(outcome["name"])
    if current_attempt and _attempt_expired(current_attempt):
        refresh_attempt(current_attempt["name"], user=user, mark_submitted=True)
        current_attempt = None

    if current_attempt:
        return _build_attempt_payload(current_attempt["name"], delivery=delivery, outcome=outcome)

    latest_attempt = _get_latest_attempt(outcome["name"])
    if latest_attempt and not _can_start_new_attempt(
        delivery, latest_attempt=latest_attempt, outcome_id=outcome["name"]
    ):
        return _build_review_payload(latest_attempt["name"], delivery=delivery, outcome=outcome)

    attempt_name = start_attempt(task_delivery=task_delivery, student=student, user=user)
    attempt_row = frappe.db.get_value("Quiz Attempt", attempt_name, ["status"], as_dict=True) or {}
    if attempt_row.get("status") != "In Progress":
        return _build_review_payload(attempt_name, delivery=delivery, outcome=outcome)
    return _build_attempt_payload(attempt_name, delivery=delivery, outcome=outcome)


def start_attempt(*, task_delivery: str, student: str, user: str) -> str:
    delivery = _get_delivery(task_delivery)
    outcome = _get_outcome(task_delivery=task_delivery, student=student)
    lock_key = f"quiz:start:{outcome['name']}"
    with frappe.cache().lock(lock_key, timeout=10):
        current_attempt = _get_latest_in_progress_attempt(outcome["name"])
        if current_attempt:
            return current_attempt["name"]

        latest_attempt = _get_latest_attempt(outcome["name"])
        if latest_attempt and not _can_start_new_attempt(
            delivery, latest_attempt=latest_attempt, outcome_id=outcome["name"]
        ):
            return latest_attempt["name"]

        attempt_number = _next_attempt_number(outcome["name"])
        question_rows = _select_questions_for_attempt(delivery, seed_hint=f"{outcome['name']}:{attempt_number}")
        started_on = now_datetime()
        expires_on = None
        time_limit_minutes = _to_int(delivery.get("quiz_time_limit_minutes"))
        if time_limit_minutes and time_limit_minutes > 0:
            expires_on = started_on + timedelta(minutes=time_limit_minutes)

        attempt_doc = frappe.get_doc(
            {
                "doctype": "Quiz Attempt",
                "task_delivery": delivery["name"],
                "task_outcome": outcome["name"],
                "task": outcome.get("task"),
                "student": outcome.get("student"),
                "student_group": outcome.get("student_group"),
                "course": outcome.get("course"),
                "academic_year": outcome.get("academic_year"),
                "school": outcome.get("school"),
                "attempt_number": attempt_number,
                "status": "In Progress",
                "started_on": started_on,
                "expires_on": expires_on,
            }
        )
        attempt_doc.insert(ignore_permissions=True)

        for position, question in enumerate(question_rows, start=1):
            option_payload, grading_payload, manual = _build_item_snapshots(
                question,
                seed_hint=f"{attempt_doc.name}:{position}",
                shuffle_choices=int(delivery.get("quiz_shuffle_choices") or 0) == 1,
            )
            frappe.get_doc(
                {
                    "doctype": "Quiz Attempt Item",
                    "quiz_attempt": attempt_doc.name,
                    "quiz_question": question["name"],
                    "position": position,
                    "question_type": question["question_type"],
                    "prompt_html": sanitize_html(question.get("prompt") or "", allow_headings_from="h3"),
                    "option_payload": json.dumps(option_payload, separators=(",", ":")) if option_payload else None,
                    "grading_payload": json.dumps(grading_payload, separators=(",", ":")),
                    "requires_manual_grading": 1 if manual else 0,
                }
            ).insert(ignore_permissions=True)

        return attempt_doc.name


def save_attempt_responses(
    *, attempt: str, responses: list[dict[str, Any]], student: str, allow_expired: bool = False
) -> dict[str, Any]:
    attempt_row, _delivery, _outcome = _get_attempt_bundle(attempt, student)
    if attempt_row.get("status") != "In Progress":
        frappe.throw(_("Quiz attempt is not open for saving."), frappe.ValidationError)
    if _attempt_expired(attempt_row) and not allow_expired:
        frappe.throw(_("Time limit expired for this quiz attempt."), frappe.ValidationError)

    response_map = _normalize_response_payload(responses)
    items = _get_attempt_items(attempt_row["name"])
    for item in items:
        payload = response_map.get(item["name"])
        if payload is None:
            continue
        updates = _response_updates_for_item(item, payload)
        if updates:
            frappe.db.set_value("Quiz Attempt Item", item["name"], updates, update_modified=True)

    return {"attempt": attempt_row["name"], "status": attempt_row.get("status")}


def submit_attempt(
    *, attempt: str, student: str, user: str, responses: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    if responses:
        save_attempt_responses(attempt=attempt, responses=responses, student=student, allow_expired=True)
    return refresh_attempt(attempt, user=user, mark_submitted=True, student=student)


def refresh_attempt(
    attempt: str, *, user: str, mark_submitted: bool = False, student: str | None = None
) -> dict[str, Any]:
    attempt_row, delivery, outcome = _get_attempt_bundle(attempt, student)
    lock_key = f"quiz:submit:{attempt_row['name']}"
    with frappe.cache().lock(lock_key, timeout=10):
        items = _get_attempt_items(attempt_row["name"])
        total_questions = len(items)
        score = 0.0
        manual_pending = False

        for item in items:
            result = _score_item(item)
            if result["updates"]:
                frappe.db.set_value("Quiz Attempt Item", item["name"], result["updates"], update_modified=True)
            if result["manual_pending"]:
                manual_pending = True
            if result["score"] is not None:
                score += float(result["score"])

        percentage = (
            None if manual_pending or total_questions <= 0 else round((score / float(total_questions)) * 100, 2)
        )
        pass_percentage = _to_float(delivery.get("quiz_pass_percentage"))
        passed = 1 if percentage is not None and (pass_percentage is None or percentage >= pass_percentage) else 0

        attempt_updates = {
            "requires_manual_review": 1 if manual_pending else 0,
            "score": None if manual_pending else score,
            "percentage": percentage,
            "passed": passed,
        }
        if mark_submitted or attempt_row.get("status") in {"Submitted", "Needs Review"}:
            attempt_updates["submitted_on"] = attempt_row.get("submitted_on") or now_datetime()
        if manual_pending:
            attempt_updates["status"] = "Needs Review"
        elif mark_submitted or attempt_row.get("status") in {"Submitted", "Needs Review"}:
            attempt_updates["status"] = "Submitted"

        frappe.db.set_value("Quiz Attempt", attempt_row["name"], attempt_updates, update_modified=True)
        _apply_outcome_effects(
            delivery=delivery,
            outcome=outcome,
            submitted=bool(mark_submitted or attempt_row.get("status") in {"Submitted", "Needs Review"}),
            manual_pending=manual_pending,
            score=None if manual_pending else score,
            percentage=percentage,
            passed=bool(passed),
            actor=user,
        )

    refreshed_attempt = frappe.db.get_value(
        "Quiz Attempt",
        attempt_row["name"],
        [
            "name",
            "status",
            "score",
            "percentage",
            "passed",
            "requires_manual_review",
            "submitted_on",
        ],
        as_dict=True,
    )
    release_view = _student_release_view(delivery, outcome["name"])
    return {
        "attempt": _public_attempt_summary(refreshed_attempt, show_grade=release_view["grade_visible"]),
        "review": _build_review_payload(
            attempt_row["name"],
            delivery=delivery,
            outcome=outcome,
            release_view=release_view,
        )["review"],
        "released_result": release_view["released_result"],
    }


def get_student_delivery_state_map(
    *, student: str, deliveries: list[dict[str, Any]], tasks_by_name: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    quiz_deliveries = [
        row
        for row in deliveries
        if (tasks_by_name.get(row.get("task"), {}).get("task_type") or "").strip() == "Quiz"
        and row.get("quiz_question_bank")
    ]
    if not quiz_deliveries:
        return {}

    delivery_ids = [row["name"] for row in quiz_deliveries if row.get("name")]
    outcomes = frappe.get_all(
        "Task Outcome",
        filters={"task_delivery": ["in", delivery_ids], "student": student},
        fields=["name", "task_delivery", "submission_status", "grading_status", "is_complete"],
        limit=0,
    )
    outcome_by_delivery = {row["task_delivery"]: row for row in outcomes if row.get("task_delivery")}
    outcome_ids = [row["name"] for row in outcomes if row.get("name")]
    attempts = (
        frappe.get_all(
            "Quiz Attempt",
            filters={"task_outcome": ["in", outcome_ids]},
            fields=[
                "name",
                "task_outcome",
                "status",
                "attempt_number",
                "score",
                "percentage",
                "passed",
                "requires_manual_review",
                "submitted_on",
                "started_on",
                "expires_on",
            ],
            order_by="attempt_number desc, modified desc",
            limit=0,
        )
        if outcome_ids
        else []
    )
    attempts_by_outcome: dict[str, list[dict[str, Any]]] = {}
    for row in attempts:
        outcome_id = row.get("task_outcome")
        if not outcome_id:
            continue
        attempts_by_outcome.setdefault(outcome_id, []).append(row)

    state_map: dict[str, dict[str, Any]] = {}
    for delivery in quiz_deliveries:
        outcome = outcome_by_delivery.get(delivery["name"])
        if not outcome:
            continue
        rows = attempts_by_outcome.get(outcome["name"], [])
        latest = rows[0] if rows else None
        current = next((row for row in rows if row.get("status") == "In Progress"), None)
        max_attempts = _to_int(delivery.get("quiz_max_attempts"))
        attempts_used = len(rows)
        pass_percentage = _to_float(delivery.get("quiz_pass_percentage"))
        latest_percentage = _to_float(latest.get("percentage")) if latest else None
        threshold_met = (
            latest_percentage is not None and pass_percentage is not None and latest_percentage >= pass_percentage
        )
        can_start = current is None and (max_attempts is None or attempts_used < max_attempts) and not threshold_met
        show_grade = delivery.get("delivery_mode") != "Assess"
        state_map[delivery["name"]] = {
            "is_practice": 1 if delivery.get("delivery_mode") != "Assess" else 0,
            "attempts_used": attempts_used,
            "max_attempts": max_attempts,
            "can_start": 1 if can_start and not latest else 0,
            "can_continue": 1 if current else 0,
            "can_retry": 1 if latest and can_start else 0,
            "latest_attempt": latest.get("name") if latest else None,
            "status_label": _delivery_status_label(current=current, latest=latest, outcome=outcome),
            "score": latest.get("score") if latest and show_grade else None,
            "percentage": latest.get("percentage") if latest and show_grade else None,
            "passed": int(latest.get("passed") or 0) if latest and show_grade else 0,
            "pass_percentage": pass_percentage,
            "time_limit_minutes": _to_int(delivery.get("quiz_time_limit_minutes")),
        }
    return state_map


def _get_delivery(task_delivery: str) -> dict[str, Any]:
    fields = [
        "name",
        "task",
        "delivery_mode",
        "grading_mode",
        "grade_scale",
        "course",
        "student_group",
        "academic_year",
        "school",
        "quiz_question_bank",
        "quiz_question_count",
        "quiz_time_limit_minutes",
        "quiz_max_attempts",
        "quiz_pass_percentage",
        "quiz_shuffle_questions",
        "quiz_shuffle_choices",
    ]
    delivery = frappe.db.get_value("Task Delivery", task_delivery, fields, as_dict=True)
    if not delivery:
        frappe.throw(_("Quiz delivery not found."))
    if not delivery.get("quiz_question_bank"):
        frappe.throw(_("This delivery is not configured as a quiz."), frappe.ValidationError)
    return delivery


def _get_outcome(*, task_delivery: str, student: str) -> dict[str, Any]:
    fields = [
        "name",
        "task_delivery",
        "task",
        "student",
        "student_group",
        "course",
        "academic_year",
        "school",
        "submission_status",
        "grading_status",
        "is_complete",
    ]
    outcome = frappe.db.get_value(
        "Task Outcome",
        {"task_delivery": task_delivery, "student": student},
        fields,
        as_dict=True,
    )
    if not outcome:
        frappe.throw(_("Quiz outcome could not be resolved for this student."), frappe.PermissionError)
    return outcome


def _get_attempt_bundle(attempt: str, student: str | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    attempt_fields = [
        "name",
        "task_delivery",
        "task_outcome",
        "student",
        "status",
        "submitted_on",
        "expires_on",
    ]
    attempt_row = frappe.db.get_value("Quiz Attempt", attempt, attempt_fields, as_dict=True)
    if not attempt_row:
        frappe.throw(_("Quiz attempt not found."), frappe.DoesNotExistError)
    if student and attempt_row.get("student") != student:
        frappe.throw(_("You do not have access to this quiz attempt."), frappe.PermissionError)
    delivery = _get_delivery(attempt_row["task_delivery"])
    outcome = _get_outcome(task_delivery=attempt_row["task_delivery"], student=attempt_row["student"])
    return attempt_row, delivery, outcome


def _get_latest_in_progress_attempt(outcome_id: str) -> dict[str, Any] | None:
    rows = frappe.get_all(
        "Quiz Attempt",
        filters={"task_outcome": outcome_id, "status": "In Progress"},
        fields=["name", "status", "expires_on", "attempt_number"],
        order_by="attempt_number desc, modified desc",
        limit=1,
    )
    return rows[0] if rows else None


def _get_latest_attempt(outcome_id: str) -> dict[str, Any] | None:
    rows = frappe.get_all(
        "Quiz Attempt",
        filters={"task_outcome": outcome_id},
        fields=["name", "status", "attempt_number", "percentage", "passed"],
        order_by="attempt_number desc, modified desc",
        limit=1,
    )
    return rows[0] if rows else None


def _next_attempt_number(outcome_id: str) -> int:
    latest = frappe.db.get_value("Quiz Attempt", {"task_outcome": outcome_id}, "max(attempt_number)")
    return int(latest or 0) + 1


def _can_start_new_attempt(delivery: dict[str, Any], *, latest_attempt: dict[str, Any] | None, outcome_id: str) -> bool:
    if _get_latest_in_progress_attempt(outcome_id):
        return False
    max_attempts = _to_int(delivery.get("quiz_max_attempts"))
    if max_attempts is not None and _next_attempt_number(outcome_id) > max_attempts:
        return False
    pass_percentage = _to_float(delivery.get("quiz_pass_percentage"))
    if latest_attempt and pass_percentage is not None:
        latest_percentage = _to_float(latest_attempt.get("percentage"))
        if latest_percentage is not None and latest_percentage >= pass_percentage:
            return False
    return True


def _select_questions_for_attempt(delivery: dict[str, Any], *, seed_hint: str) -> list[dict[str, Any]]:
    questions = frappe.get_all(
        "Quiz Question",
        filters={"question_bank": delivery.get("quiz_question_bank"), "is_published": 1},
        fields=["name", "question_type", "prompt", "accepted_answers", "explanation"],
        order_by="modified asc, name asc",
        limit=0,
    )
    if not questions:
        frappe.throw(_("Quiz Question Bank has no published questions."))

    count = _to_int(delivery.get("quiz_question_count"))
    count = count or len(questions)
    if count > len(questions):
        frappe.throw(_("Quiz Question Bank does not have enough published questions for this delivery."))

    rnd = random.Random(_seed_for_delivery(delivery, seed_hint))
    selected = list(questions)
    if int(delivery.get("quiz_shuffle_questions") or 0) == 1:
        rnd.shuffle(selected)
    selected = selected[:count]
    return selected


def _seed_for_delivery(delivery: dict[str, Any], seed_hint: str) -> int:
    seed_text = "|".join(
        [
            str(delivery.get("name") or ""),
            str(delivery.get("quiz_question_bank") or ""),
            str(delivery.get("quiz_question_count") or ""),
            str(seed_hint or ""),
        ]
    )
    return int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:12], 16)


def _build_item_snapshots(
    question: dict[str, Any], *, seed_hint: str, shuffle_choices: bool
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    option_rows = frappe.get_all(
        "Quiz Question Option",
        filters={
            "parent": question["name"],
            "parenttype": "Quiz Question",
            "parentfield": "options",
        },
        fields=["name", "option_text", "is_correct", "idx"],
        order_by="idx asc, name asc",
        limit=0,
    )
    option_payload = [{"id": row["name"], "text": row.get("option_text") or ""} for row in option_rows]
    if option_payload and question["question_type"] in CHOICE_TYPES and shuffle_choices:
        rnd = random.Random(int(hashlib.sha256(f"{question['name']}|{seed_hint}".encode("utf-8")).hexdigest()[:12], 16))
        rnd.shuffle(option_payload)

    grading_payload: dict[str, Any] = {"question_type": question["question_type"]}
    manual = question["question_type"] in MANUAL_TYPES
    if question["question_type"] in CHOICE_TYPES:
        grading_payload["correct_ids"] = [row["name"] for row in option_rows if int(row.get("is_correct") or 0) == 1]
    elif question["question_type"] == "Short Answer":
        grading_payload["accepted_answers"] = [
            line.strip().lower() for line in str(question.get("accepted_answers") or "").splitlines() if line.strip()
        ]
    else:
        manual = True
    grading_payload["explanation"] = sanitize_html(question.get("explanation") or "", allow_headings_from="h4")
    return option_payload, grading_payload, manual


def _normalize_response_payload(responses: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    response_map: dict[str, dict[str, Any]] = {}
    for row in responses or []:
        item_id = str((row or {}).get("item_id") or "").strip()
        if not item_id:
            continue
        response_map[item_id] = row or {}
    return response_map


def _get_attempt_items(attempt_name: str) -> list[dict[str, Any]]:
    return frappe.get_all(
        "Quiz Attempt Item",
        filters={"quiz_attempt": attempt_name},
        fields=[
            "name",
            "quiz_attempt",
            "quiz_question",
            "position",
            "question_type",
            "prompt_html",
            "option_payload",
            "grading_payload",
            "response_text",
            "response_payload",
            "awarded_score",
            "is_correct",
            "requires_manual_grading",
        ],
        order_by="position asc, name asc",
        limit=0,
    )


def _response_updates_for_item(item: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    question_type = (item.get("question_type") or "").strip()
    updates: dict[str, Any] = {}
    if question_type in CHOICE_TYPES:
        selected = payload.get("selected_option_ids") or payload.get("selected_options") or []
        if isinstance(selected, str):
            selected = [selected]
        selected = [str(value).strip() for value in selected if str(value).strip()]
        updates["response_payload"] = json.dumps(selected, separators=(",", ":"))
        updates["response_text"] = None
    else:
        text_value = str(payload.get("response_text") or "").strip()
        updates["response_text"] = text_value or None
        updates["response_payload"] = None
    return updates


def _score_item(item: dict[str, Any]) -> dict[str, Any]:
    question_type = (item.get("question_type") or "").strip()
    grading_payload = json.loads(item.get("grading_payload") or "{}")
    if question_type in MANUAL_TYPES:
        if item.get("awarded_score") not in (None, ""):
            score = float(item.get("awarded_score") or 0)
            return {
                "score": score,
                "manual_pending": False,
                "updates": {"is_correct": 1 if score >= 1 else 0, "requires_manual_grading": 0},
            }
        return {
            "score": None,
            "manual_pending": True,
            "updates": {"requires_manual_grading": 1, "is_correct": 0, "awarded_score": None},
        }

    if question_type in CHOICE_TYPES:
        selected = json.loads(item.get("response_payload") or "[]")
        selected = sorted(str(value).strip() for value in selected if str(value).strip())
        correct = sorted(str(value).strip() for value in grading_payload.get("correct_ids") or [])
        is_correct = 1 if selected == correct and correct else 0
        score = float(is_correct)
        return {
            "score": score,
            "manual_pending": False,
            "updates": {"is_correct": is_correct, "awarded_score": score, "requires_manual_grading": 0},
        }

    response_text = str(item.get("response_text") or "").strip().lower()
    accepted = [str(value).strip().lower() for value in grading_payload.get("accepted_answers") or []]
    is_correct = 1 if response_text and response_text in accepted else 0
    score = float(is_correct)
    return {
        "score": score,
        "manual_pending": False,
        "updates": {"is_correct": is_correct, "awarded_score": score, "requires_manual_grading": 0},
    }


def _apply_outcome_effects(
    *,
    delivery: dict[str, Any],
    outcome: dict[str, Any],
    submitted: bool,
    manual_pending: bool,
    score: float | None,
    percentage: float | None,
    passed: bool,
    actor: str,
) -> None:
    updates: dict[str, Any] = {}
    is_assessed = delivery.get("delivery_mode") == "Assess"
    now_value = now_datetime()

    if submitted and is_assessed:
        updates["submission_status"] = "Submitted"
    if not is_assessed:
        updates["grading_status"] = "Not Applicable"
        completion_met = True if percentage is None and not delivery.get("quiz_pass_percentage") else passed
        updates["is_complete"] = 1 if completion_met else 0
        updates["completed_on"] = now_value if completion_met else None
        if not completion_met:
            updates["official_score"] = None
            updates["official_grade"] = None
            updates["official_grade_value"] = None
        frappe.db.set_value("Task Outcome", outcome["name"], updates, update_modified=True)
        return

    if manual_pending:
        updates.update(
            {
                "grading_status": "Needs Review",
                "is_complete": 0,
                "completed_on": None,
                "official_score": None,
                "official_grade": None,
                "official_grade_value": None,
            }
        )
        frappe.db.set_value("Task Outcome", outcome["name"], updates, update_modified=True)
        return

    grade_symbol = None
    grade_value = None
    grade_scale = delivery.get("grade_scale")
    if grade_scale and score is not None:
        grade_symbol, grade_value = task_outcome_service.resolve_grade_for_score(grade_scale, score)

    updates.update(
        {
            "grading_status": "Finalized",
            "official_score": score,
            "official_grade": grade_symbol,
            "official_grade_value": grade_value,
            "is_complete": 1,
            "completed_on": now_value,
            "published_on": None,
            "published_by": None,
            "is_published": 0,
        }
    )
    frappe.db.set_value("Task Outcome", outcome["name"], updates, update_modified=True)


def _build_attempt_payload(attempt_name: str, *, delivery: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    attempt = frappe.db.get_value(
        "Quiz Attempt",
        attempt_name,
        [
            "name",
            "attempt_number",
            "status",
            "started_on",
            "expires_on",
            "submitted_on",
            "score",
            "percentage",
            "passed",
            "requires_manual_review",
        ],
        as_dict=True,
    )
    items = _get_attempt_items(attempt_name)
    show_grade = delivery.get("delivery_mode") != "Assess"
    return {
        "mode": "attempt",
        "session": _base_session_payload(
            delivery=delivery,
            outcome=outcome,
            attempt=attempt,
            show_grade=show_grade,
        ),
        "items": [
            {
                "item_id": item["name"],
                "position": item.get("position"),
                "question_type": item.get("question_type"),
                "prompt_html": item.get("prompt_html"),
                "options": json.loads(item.get("option_payload") or "[]"),
                "response_text": item.get("response_text"),
                "selected_option_ids": json.loads(item.get("response_payload") or "[]")
                if item.get("question_type") in CHOICE_TYPES
                else [],
            }
            for item in items
        ],
        "released_result": None,
    }


def _build_review_payload(
    attempt_name: str,
    *,
    delivery: dict[str, Any],
    outcome: dict[str, Any],
    release_view: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attempt = frappe.db.get_value(
        "Quiz Attempt",
        attempt_name,
        [
            "name",
            "attempt_number",
            "status",
            "started_on",
            "expires_on",
            "submitted_on",
            "score",
            "percentage",
            "passed",
            "requires_manual_review",
        ],
        as_dict=True,
    )
    items = _get_attempt_items(attempt_name)
    release_view = release_view or _student_release_view(delivery, outcome["name"])
    review_items = []
    for item in items:
        grading_payload = json.loads(item.get("grading_payload") or "{}")
        review_items.append(
            _public_review_item(
                item,
                grading_payload=grading_payload,
                show_grade=release_view["grade_visible"],
                show_feedback=release_view["feedback_visible"],
            )
        )
    return {
        "mode": "review",
        "session": _base_session_payload(
            delivery=delivery,
            outcome=outcome,
            attempt=attempt,
            show_grade=release_view["grade_visible"],
        ),
        "review": {
            "attempt": _public_attempt_summary(attempt, show_grade=release_view["grade_visible"]),
            "items": review_items,
        },
        "released_result": release_view["released_result"],
    }


def _base_session_payload(
    *,
    delivery: dict[str, Any],
    outcome: dict[str, Any],
    attempt: dict[str, Any],
    show_grade: bool,
) -> dict[str, Any]:
    task_title = frappe.db.get_value("Task", delivery["task"], "title") or delivery["task"]
    return {
        "task_delivery": delivery["name"],
        "task": delivery.get("task"),
        "title": task_title,
        "course": delivery.get("course"),
        "is_practice": 1 if delivery.get("delivery_mode") != "Assess" else 0,
        "attempt_id": attempt.get("name"),
        "attempt_number": attempt.get("attempt_number"),
        "status": attempt.get("status"),
        "started_on": _serialize_scalar(attempt.get("started_on")),
        "expires_on": _serialize_scalar(attempt.get("expires_on")),
        "submitted_on": _serialize_scalar(attempt.get("submitted_on")),
        "score": attempt.get("score") if show_grade else None,
        "percentage": attempt.get("percentage") if show_grade else None,
        "passed": int(attempt.get("passed") or 0) if show_grade else 0,
        "requires_manual_review": int(attempt.get("requires_manual_review") or 0),
        "max_attempts": _to_int(delivery.get("quiz_max_attempts")),
        "pass_percentage": _to_float(delivery.get("quiz_pass_percentage")),
        "outcome_id": outcome.get("name"),
    }


def _delivery_status_label(
    *, current: dict[str, Any] | None, latest: dict[str, Any] | None, outcome: dict[str, Any]
) -> str:
    if current:
        return "In Progress"
    if latest:
        if latest.get("requires_manual_review"):
            return "Awaiting Review"
        if int(latest.get("passed") or 0) == 1:
            return "Passed"
        return "Submitted"
    if int(outcome.get("is_complete") or 0) == 1:
        return "Completed"
    return "Not Started"


def _student_release_view(delivery: dict[str, Any], outcome_id: str) -> dict[str, Any]:
    if delivery.get("delivery_mode") != "Assess":
        return {
            "grade_visible": True,
            "feedback_visible": True,
            "released_result": None,
        }

    released_result = task_feedback_service.build_released_result_payload(outcome_id, audience="student")
    return {
        "grade_visible": bool(released_result.get("grade_visible")),
        "feedback_visible": bool(released_result.get("feedback_visible")),
        "released_result": released_result,
    }


def _public_attempt_summary(attempt: dict[str, Any], *, show_grade: bool) -> dict[str, Any]:
    return {
        "attempt_id": attempt.get("name"),
        "attempt_number": attempt.get("attempt_number"),
        "status": attempt.get("status"),
        "submitted_on": _serialize_scalar(attempt.get("submitted_on")),
        "score": attempt.get("score") if show_grade else None,
        "percentage": attempt.get("percentage") if show_grade else None,
        "passed": int(attempt.get("passed") or 0) if show_grade else 0,
        "requires_manual_review": int(attempt.get("requires_manual_review") or 0),
    }


def _public_review_item(
    item: dict[str, Any], *, grading_payload: dict[str, Any], show_grade: bool, show_feedback: bool
) -> dict[str, Any]:
    return {
        "item_id": item["name"],
        "position": item.get("position"),
        "question_type": item.get("question_type"),
        "prompt_html": item.get("prompt_html"),
        "options": json.loads(item.get("option_payload") or "[]"),
        "response_text": item.get("response_text"),
        "selected_option_ids": json.loads(item.get("response_payload") or "[]")
        if item.get("question_type") in CHOICE_TYPES
        else [],
        "awarded_score": item.get("awarded_score") if show_grade else None,
        "is_correct": int(item.get("is_correct") or 0) if show_feedback else 0,
        "requires_manual_grading": int(item.get("requires_manual_grading") or 0),
        "explanation_html": grading_payload.get("explanation") if show_feedback else None,
        "correct_option_ids": grading_payload.get("correct_ids") if show_feedback else [],
        "accepted_answers": grading_payload.get("accepted_answers") if show_feedback else [],
    }


def _attempt_expired(attempt: dict[str, Any]) -> bool:
    expires_on = attempt.get("expires_on")
    if not expires_on:
        return False
    return get_datetime(expires_on) <= now_datetime()


def _serialize_scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat(sep=" ")
        except TypeError:
            return value.isoformat()
    return value


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None
