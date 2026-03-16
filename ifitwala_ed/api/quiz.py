# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.api import courses as courses_api
from ifitwala_ed.assessment import quiz_service


@frappe.whitelist()
def list_question_banks(course: str | None = None):
    if not _can_manage_quizzes():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    filters: dict[str, object] = {"is_published": 1}
    if course:
        filters["course"] = course

    return frappe.get_all(
        "Quiz Question Bank",
        filters=filters,
        fields=["name", "bank_title", "course"],
        order_by="bank_title asc, name asc",
        limit_page_length=200,
    )


@frappe.whitelist()
def open_session(task_delivery: str):
    student = _require_student_scope(task_delivery)
    return quiz_service.open_quiz_session(task_delivery=task_delivery, student=student, user=frappe.session.user)


@frappe.whitelist()
def save_attempt(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    attempt = (data.get("attempt") or data.get("attempt_id") or "").strip()
    if not attempt:
        frappe.throw(_("Quiz Attempt is required."))
    student = _require_student_for_attempt(attempt)
    responses = data.get("responses") or []
    return quiz_service.save_attempt_responses(attempt=attempt, responses=responses, student=student)


@frappe.whitelist()
def submit_attempt(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    attempt = (data.get("attempt") or data.get("attempt_id") or "").strip()
    if not attempt:
        frappe.throw(_("Quiz Attempt is required."))
    student = _require_student_for_attempt(attempt)
    responses = data.get("responses") or []
    return quiz_service.submit_attempt(
        attempt=attempt,
        responses=responses,
        student=student,
        user=frappe.session.user,
    )


def _normalize_payload(payload, kwargs):
    data = payload if payload is not None else kwargs
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw(_("Payload must be a dict."))
    return data


def _require_student_scope(task_delivery: str) -> str:
    student = courses_api._require_student_name_for_session_user()
    delivery = frappe.db.get_value("Task Delivery", task_delivery, ["course"], as_dict=True) or {}
    course_id = delivery.get("course")
    scope = courses_api._build_student_course_scope(student)
    if not course_id or course_id not in scope:
        frappe.throw(_("You do not have access to this quiz."), frappe.PermissionError)
    return student


def _require_student_for_attempt(attempt: str) -> str:
    student = courses_api._require_student_name_for_session_user()
    row = frappe.db.get_value("Quiz Attempt", attempt, ["student", "task_delivery"], as_dict=True) or {}
    if not row or row.get("student") != student:
        frappe.throw(_("You do not have access to this quiz attempt."), frappe.PermissionError)
    _require_student_scope(row.get("task_delivery"))
    return student


def _can_manage_quizzes() -> bool:
    roles = set(frappe.get_roles(frappe.session.user))
    return bool(roles & {"System Manager", "Academic Admin", "Instructor", "Curriculum Coordinator"})
