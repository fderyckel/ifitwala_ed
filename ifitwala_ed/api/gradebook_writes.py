# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.assessment import quiz_service, task_contribution_service, task_outcome_service


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


def repair_task_roster(api, task: str):
    if not api._can_write_gradebook():
        frappe.throw(_("Not permitted."), frappe.PermissionError)
    api._require(task, "Task Delivery")

    delivery = frappe.get_doc("Task Delivery", task)
    api._assert_group_access(delivery.student_group)

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
    api._assert_group_access(delivery_row.get("student_group"))

    grading_mode = (delivery_row.get("grading_mode") or "").strip()
    delivery_mode = (delivery_row.get("delivery_mode") or "").strip()
    allow_feedback = api._bool_flag(delivery_row.get("allow_feedback"))
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
    if status_value is not None and delivery_mode != "Assess":
        frappe.throw(_("Grading status can only be updated for assessed work."))
    if status_value is not None or complete_provided or visibility_provided:
        outcome_doc = frappe.get_doc("Task Outcome", task_student)
        if status_value is not None:
            outcome_doc.grading_status = status_value
        if complete_provided:
            outcome_doc.is_complete = 1 if api._bool_flag(payload.get("complete")) else 0
        if visibility_provided:
            publish_flag = api._bool_flag(payload.get("visible_to_student")) or api._bool_flag(
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
        "mark_awarded": api._coerce_float(fresh.get("official_score")),
        "feedback": fresh.get("official_feedback"),
        "status": fresh.get("grading_status"),
        "complete": int(fresh.get("is_complete") or 0),
        "visible_to_student": int(fresh.get("is_published") or 0),
        "visible_to_guardian": int(fresh.get("is_published") or 0),
        "updated_on": fresh.get("modified"),
    }
