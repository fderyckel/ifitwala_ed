# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.api import outcome_publish
from ifitwala_ed.assessment import (
    quiz_service,
    task_contribution_service,
    task_feedback_artifact_service,
    task_feedback_comment_bank_service,
    task_feedback_service,
    task_feedback_thread_service,
    task_outcome_service,
)


def save_draft(api, payload=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    api._reject_official_fields(data)
    outcome_id = api._get_payload_value(data, "task_outcome", "outcome")
    api._require(outcome_id, "Task Outcome")
    submission_id = api._get_existing_submission_id(outcome_id, data)
    if submission_id:
        data["task_submission"] = submission_id
    result = task_contribution_service.save_draft_contribution(data, contributor=frappe.session.user)
    return {
        "result": result,
        "outcome": api._get_outcome_summary(outcome_id),
    }


def save_feedback_draft(api, payload=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    outcome_id = api._get_payload_value(data, "outcome_id", "task_outcome")
    submission_id = api._get_payload_value(data, "submission_id", "task_submission")
    api._require(outcome_id, "Task Outcome")
    api._require(submission_id, "Task Submission")
    _assert_outcome_access(api, outcome_id)
    result = task_feedback_service.save_feedback_workspace_draft(data, actor=frappe.session.user)
    return {"feedback_workspace": result}


def save_feedback_publication(api, payload=None, **kwargs):
    if not api._can_write_gradebook() and not api._is_academic_adminish():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    outcome_id = api._get_payload_value(data, "outcome_id", "task_outcome")
    submission_id = api._get_payload_value(data, "submission_id", "task_submission")
    api._require(outcome_id, "Task Outcome")
    api._require(submission_id, "Task Submission")
    _assert_outcome_access(api, outcome_id)
    result = task_feedback_service.save_feedback_publication(data, actor=frappe.session.user)
    return {"feedback_workspace": result}


def save_feedback_comment_bank_entry(api, payload=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    outcome_id = api._get_payload_value(data, "outcome_id", "task_outcome")
    api._require(outcome_id, "Task Outcome")
    _assert_outcome_access(api, outcome_id)
    result = task_feedback_comment_bank_service.save_comment_bank_entry(data, actor=frappe.session.user)
    return {"comment_bank": result}


def save_feedback_thread_reply(api, payload=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    outcome_id = api._get_payload_value(data, "outcome_id", "task_outcome")
    api._require(outcome_id, "Task Outcome")
    _assert_outcome_access(api, outcome_id)
    result = task_feedback_thread_service.save_instructor_reply(data, actor=frappe.session.user)
    return {"thread": result}


def save_feedback_thread_state(api, payload=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    outcome_id = api._get_payload_value(data, "outcome_id", "task_outcome")
    api._require(outcome_id, "Task Outcome")
    _assert_outcome_access(api, outcome_id)
    result = task_feedback_thread_service.save_instructor_thread_state(data, actor=frappe.session.user)
    return {"thread": result}


def export_feedback_pdf(api, payload=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    outcome_id = api._get_payload_value(data, "outcome_id", "task_outcome")
    submission_id = api._get_payload_value(data, "submission_id", "task_submission")
    api._require(outcome_id, "Task Outcome")
    _assert_outcome_access(api, outcome_id)
    artifact = task_feedback_artifact_service.export_released_feedback_pdf(
        outcome_id,
        audience="student",
        submission_id=submission_id,
    )
    return {"artifact": artifact}


def submit_contribution(api, payload=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    api._reject_official_fields(data)
    outcome_id = api._get_payload_value(data, "task_outcome", "outcome")
    api._require(outcome_id, "Task Outcome")
    data["task_submission"] = api._resolve_or_create_stub_submission_id(outcome_id, data)
    result = task_contribution_service.submit_contribution(data, contributor=frappe.session.user)
    return {
        "ok": True,
        "outcome_update": result.get("outcome_update"),
        "result": result,
    }


def moderator_action(api, payload=None, **kwargs):
    if not api._is_academic_adminish():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    api._reject_official_fields(data)
    outcome_id = api._get_payload_value(data, "task_outcome", "outcome")
    api._require(outcome_id, "Task Outcome")
    data["task_submission"] = api._resolve_or_create_stub_submission_id(outcome_id, data)
    result = task_contribution_service.apply_moderator_action(data, contributor=frappe.session.user)
    return {
        "ok": True,
        "outcome_update": result.get("outcome_update"),
        "result": result,
    }


def mark_new_submission_seen(api, outcome: str):
    api._require(outcome, "Task Outcome")
    if not api._can_write_gradebook() and not api._is_academic_adminish():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    return task_outcome_service.mark_new_submission_seen(outcome)


def save_task_quiz_manual_review(api, task: str, grades=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    api._require(task, "Task Delivery")

    raw_rows = grades if grades is not None else kwargs.get("grades")
    if isinstance(raw_rows, str):
        raw_rows = frappe.parse_json(raw_rows)
    if raw_rows is None:
        payload = api._normalize_payload(None, kwargs)
        raw_rows = payload.get("grades")
    rows = raw_rows
    if not isinstance(rows, list) or not rows:
        frappe.throw(_("Grades must be a non-empty list."))

    delivery = api._resolve_delivery(task)
    api._assert_group_access(delivery.get("student_group"))
    api._require_manual_quiz_review_delivery(delivery)

    requested_items: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            frappe.throw(_("Each quiz manual review row must be an object."))
        item_id = str(row.get("item_id") or "").strip()
        if not item_id:
            frappe.throw(_("Quiz Attempt Item is required."))
        score = api._coerce_float(row.get("awarded_score"))
        if score is None:
            frappe.throw(_("Awarded score is required for manual quiz grading."))
        if score < 0 or score > 1:
            frappe.throw(_("Awarded score must stay between 0 and 1 for quiz manual grading."))
        requested_items[item_id] = score

    item_rows = frappe.get_all(
        "Quiz Attempt Item",
        filters={"name": ["in", list(requested_items.keys())]},
        fields=["name", "quiz_attempt", "question_type"],
        limit=0,
    )
    if len(item_rows) != len(requested_items):
        frappe.throw(_("One or more quiz attempt items could not be found."))

    attempt_ids = [row.get("quiz_attempt") for row in item_rows if row.get("quiz_attempt")]
    attempt_rows = frappe.get_all(
        "Quiz Attempt",
        filters={"name": ["in", list(set(attempt_ids))]},
        fields=["name", "task_delivery", "student", "status"],
        limit=0,
    )
    attempt_map = {row.get("name"): row for row in attempt_rows if row.get("name")}

    for item in item_rows:
        if item.get("question_type") not in quiz_service.MANUAL_TYPES:
            frappe.throw(_("Only manually graded quiz items can be updated from this surface."))
        attempt = attempt_map.get(item.get("quiz_attempt"))
        if not attempt or attempt.get("task_delivery") != delivery.get("name"):
            frappe.throw(_("Quiz attempt item does not belong to the selected delivery."), frappe.PermissionError)
        if attempt.get("status") not in {"Submitted", "Needs Review"}:
            frappe.throw(_("Only submitted quiz attempts can be manually graded."))

    touched_attempts = []
    for item in item_rows:
        frappe.db.set_value(
            "Quiz Attempt Item",
            item.get("name"),
            {"awarded_score": requested_items[item["name"]]},
            update_modified=True,
        )
        touched_attempts.append(item.get("quiz_attempt"))

    for attempt_id in dict.fromkeys(touched_attempts):
        attempt = attempt_map.get(attempt_id) or {}
        quiz_service.refresh_attempt(
            attempt_id,
            user=frappe.session.user,
            mark_submitted=True,
            student=attempt.get("student"),
        )

    return {
        "updated_item_count": len(item_rows),
        "updated_attempt_count": len(dict.fromkeys(touched_attempts)),
    }


def update_task_student(api, task_student: str, updates=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    api._require(task_student, "Task Outcome")

    payload = updates if updates is not None else kwargs
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("Updates payload must be a dict."))

    outcome_row = frappe.db.get_value(
        "Task Outcome",
        task_student,
        ["name", "task_delivery", "official_score", "grading_status", "is_published"],
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
    api._assert_group_access(delivery_row.get("student_group"))

    grading_mode = (delivery_row.get("grading_mode") or "").strip()
    delivery_mode = (delivery_row.get("delivery_mode") or "").strip()
    allow_feedback = api._bool_flag(delivery_row.get("allow_feedback"))
    assessed_boolean_mode = delivery_mode == "Assess" and grading_mode in {"Binary", "Completion"}
    assign_only_mode = delivery_mode == "Assign Only"
    score_provided = "mark_awarded" in payload and payload.get("mark_awarded") not in (None, "")
    feedback_provided = "feedback" in payload
    criteria_provided = isinstance(payload.get("criteria_scores"), list)
    complete_provided = "complete" in payload

    if score_provided and grading_mode != "Points":
        frappe.throw(_("Points can only be recorded for points grading."))

    if criteria_provided and grading_mode != "Criteria":
        frappe.throw(_("Criteria scores can only be recorded for criteria grading."))

    if complete_provided and not (assessed_boolean_mode or assign_only_mode):
        frappe.throw(_("Completion can only be recorded for completion, binary, or assign-only work."))

    if feedback_provided and not allow_feedback:
        frappe.throw(_("Comments are not enabled for this delivery."))

    if score_provided or feedback_provided or criteria_provided or (complete_provided and assessed_boolean_mode):
        contribution_payload = {"task_outcome": task_student}
        if score_provided:
            contribution_payload["score"] = payload.get("mark_awarded")
        elif grading_mode == "Points" and outcome_row.get("official_score") not in (None, ""):
            contribution_payload["score"] = outcome_row.get("official_score")

        if feedback_provided:
            contribution_payload["feedback"] = payload.get("feedback")

        if assessed_boolean_mode and complete_provided:
            is_complete = 1 if api._bool_flag(payload.get("complete")) else 0
            contribution_payload["judgment_code"] = (
                "complete"
                if grading_mode == "Completion" and is_complete
                else "incomplete"
                if grading_mode == "Completion"
                else "yes"
                if is_complete
                else "no"
            )

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
                        "level_points": api._coerce_float(row.get("level_points")),
                        "feedback": row.get("feedback"),
                    }
                )
            if rubric_scores:
                contribution_payload["rubric_scores"] = rubric_scores

        should_submit_contribution = True
        if grading_mode == "Criteria" and not contribution_payload.get("rubric_scores"):
            existing_scores = api._build_rubric_scores_from_outcome(task_student)
            if existing_scores:
                contribution_payload["rubric_scores"] = existing_scores
            elif criteria_provided:
                frappe.throw(_("Criteria levels are required before saving criteria marks."))
            elif not feedback_provided:
                should_submit_contribution = False

        if should_submit_contribution:
            api._reject_official_fields(contribution_payload)
            contribution_payload["task_submission"] = api._resolve_or_create_stub_submission_id(
                task_student, contribution_payload
            )
            task_contribution_service.submit_contribution(contribution_payload, contributor=frappe.session.user)

    status_value = api._normalize_grading_status(payload.get("status")) if "status" in payload else None
    visibility_provided = "visible_to_student" in payload or "visible_to_guardian" in payload
    is_published = api._bool_flag(outcome_row.get("is_published"))
    direct_complete_write = complete_provided and assign_only_mode
    if status_value is not None and delivery_mode != "Assess":
        frappe.throw(_("Grading status can only be updated for assessed work."))
    if status_value == "Released":
        frappe.throw(_("Use the Release action to release outcomes."))
    if status_value is not None and is_published:
        frappe.throw(_("Unrelease this outcome before changing grading status."))
    if status_value is not None or direct_complete_write or visibility_provided:
        outcome_doc = frappe.get_doc("Task Outcome", task_student) if status_value is not None else None
        if status_value is not None:
            outcome_doc.grading_status = status_value
        if direct_complete_write:
            task_outcome_service.set_assign_only_completion(
                task_student,
                is_complete=1 if api._bool_flag(payload.get("complete")) else 0,
                ignore_permissions=False,
            )
        if visibility_provided:
            publish_flag = api._bool_flag(payload.get("visible_to_student")) or api._bool_flag(
                payload.get("visible_to_guardian")
            )
            if not publish_flag and not api._is_academic_adminish():
                frappe.throw(_("Not permitted."), frappe.PermissionError)
            if status_value is not None:
                outcome_doc.save(ignore_permissions=False)
            outcome_publish._bulk_update_publish(
                [task_student],
                {
                    "is_published": 1 if publish_flag else 0,
                    "published_on": now_datetime() if publish_flag else None,
                    "published_by": frappe.session.user if publish_flag else None,
                },
            )
        elif status_value is not None:
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
        "mark_awarded": api._coerce_float(fresh.get("official_score")),
        "feedback": fresh.get("official_feedback"),
        "status": fresh.get("grading_status"),
        "complete": int(fresh.get("is_complete") or 0),
        "visible_to_student": int(fresh.get("is_published") or 0),
        "visible_to_guardian": int(fresh.get("is_published") or 0),
        "updated_on": fresh.get("modified"),
    }


def batch_mark_completion(api, payload=None, **kwargs):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    data = api._normalize_payload(payload, kwargs)
    task_delivery = data.get("task_delivery") or data.get("task")
    api._require(task_delivery, "Task Delivery")

    target_complete = data.get("target_complete", True)
    if not api._bool_flag(target_complete):
        frappe.throw(_("Batch completion currently only supports marking work complete."))

    delivery_row = (
        frappe.db.get_value(
            "Task Delivery",
            task_delivery,
            ["name", "student_group", "delivery_mode", "grading_mode"],
            as_dict=True,
        )
        or {}
    )
    if not delivery_row:
        frappe.throw(_("Task Delivery not found."))

    api._assert_group_access(delivery_row.get("student_group"))

    delivery_mode = (delivery_row.get("delivery_mode") or "").strip()
    grading_mode = (delivery_row.get("grading_mode") or "").strip()
    assessed_completion_mode = delivery_mode == "Assess" and grading_mode == "Completion"
    assign_only_mode = delivery_mode == "Assign Only"
    if not (assessed_completion_mode or assign_only_mode):
        frappe.throw(_("Batch completion is only available for completion or assign-only work."))

    outcome_filters = {"task_delivery": task_delivery}
    requested_outcome_ids = _normalize_outcome_id_list(data.get("outcome_ids"))
    if requested_outcome_ids is not None:
        if not requested_outcome_ids:
            return _empty_batch_completion_response(task_delivery)
        outcome_filters["name"] = ["in", requested_outcome_ids]

    outcomes = frappe.get_all(
        "Task Outcome",
        filters=outcome_filters,
        fields=["name", "is_complete", "is_published"],
        order_by="student asc, name asc",
        limit=0,
    )
    if len(outcomes) > 500:
        frappe.throw(_("Batch completion is limited to 500 outcomes at a time."))

    updated = []
    already_complete = []
    skipped_published = []

    for outcome in outcomes:
        outcome_id = outcome.get("name")
        if not outcome_id:
            continue
        if api._bool_flag(outcome.get("is_published")):
            skipped_published.append(outcome_id)
            continue
        if api._bool_flag(outcome.get("is_complete")):
            already_complete.append(outcome_id)
            continue

        if assessed_completion_mode:
            result = task_contribution_service.submit_contribution(
                {"task_outcome": outcome_id, "judgment_code": "complete"},
                contributor=frappe.session.user,
            )
            outcome_update = result.get("outcome_update") if isinstance(result, dict) else {}
            updated.append(
                {
                    "outcome": outcome_id,
                    "is_complete": 1,
                    "grading_status": (outcome_update or {}).get("grading_status"),
                }
            )
            continue

        result = task_outcome_service.set_assign_only_completion(
            outcome_id,
            is_complete=1,
            ignore_permissions=False,
        )
        updated.append(
            {
                "outcome": outcome_id,
                "is_complete": result.get("is_complete"),
                "completed_on": result.get("completed_on"),
            }
        )

    return {
        "task_delivery": task_delivery,
        "target_complete": 1,
        "total_count": len(outcomes),
        "updated_count": len(updated),
        "already_complete_count": len(already_complete),
        "skipped_published_count": len(skipped_published),
        "updated": updated,
        "already_complete": already_complete,
        "skipped_published": skipped_published,
    }


def _normalize_outcome_id_list(value):
    if value in (None, ""):
        return None
    if isinstance(value, str):
        value = frappe.parse_json(value)
    if not isinstance(value, list):
        frappe.throw(_("Outcome IDs must be a list."))
    return [str(entry).strip() for entry in value if str(entry or "").strip()]


def _empty_batch_completion_response(task_delivery):
    return {
        "task_delivery": task_delivery,
        "target_complete": 1,
        "total_count": 0,
        "updated_count": 0,
        "already_complete_count": 0,
        "skipped_published_count": 0,
        "updated": [],
        "already_complete": [],
        "skipped_published": [],
    }


def _assert_outcome_access(api, outcome_id: str):
    outcome_row = frappe.db.get_value("Task Outcome", outcome_id, ["task_delivery"], as_dict=True)
    if not outcome_row:
        frappe.throw(_("Task Outcome not found."))
    delivery = api._resolve_delivery(outcome_row.get("task_delivery"))
    api._assert_group_access(delivery.get("student_group"))
