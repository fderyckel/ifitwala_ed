# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import hashlib
from time import perf_counter
from types import SimpleNamespace

import frappe
from frappe import _

from ifitwala_ed.api import courses as courses_api
from ifitwala_ed.assessment import quiz_service
from ifitwala_ed.curriculum import planning


@frappe.whitelist()
def list_question_banks(course: str | None = None):
    if not _can_manage_quizzes():
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    user = frappe.session.user
    roles = set(frappe.get_roles(user) or [])
    filters: dict[str, object] = {"is_published": 1}
    course_name = planning.normalize_text(course)
    if planning.user_has_global_curriculum_access(user, roles):
        if course_name:
            filters["course"] = course_name
    elif course_name:
        planning.assert_can_read_course_curriculum(
            user,
            course_name,
            roles,
            action_label=_("view quiz banks for this course"),
        )
        filters["course"] = course_name
    else:
        managed_courses = planning.get_curriculum_manageable_course_names(user, roles)
        if not managed_courses:
            return []
        filters["course"] = ["in", managed_courses]

    return frappe.get_all(
        "Quiz Question Bank",
        filters=filters,
        fields=["name", "bank_title", "course"],
        order_by="bank_title asc, name asc",
        limit=200,
    )


@frappe.whitelist()
def save_question_bank(payload=None, **kwargs):
    started_at = perf_counter()
    status = "success"
    course_plan = ""
    question_bank_name = ""
    question_count = 0
    try:
        data = _normalize_payload(payload, kwargs)
        course_plan = planning.normalize_text(data.get("course_plan"))
        question_bank_name = planning.normalize_text(
            data.get("quiz_question_bank") or data.get("question_bank") or data.get("name")
        )
        if question_bank_name:
            bank_doc = frappe.get_doc("Quiz Question Bank", question_bank_name)
            _require_course_plan_write_access(course_plan, expected_course=bank_doc.course)
            if data.get("expected_modified") is not None:
                planning.assert_record_modified_matches(
                    expected_modified=data.get("expected_modified"),
                    current_modified=_question_bank_record_modified(question_bank_name),
                    section_label=_("Quiz question bank"),
                )
        else:
            course_row = _require_course_plan_write_access(course_plan)
            bank_doc = frappe.new_doc("Quiz Question Bank")
            bank_doc.course = course_row.get("course")

        bank_title = planning.normalize_text(data.get("bank_title"))
        if not bank_title:
            frappe.throw(_("Bank Title is required."))

        bank_doc.bank_title = bank_title
        bank_doc.description = planning.normalize_long_text(data.get("description"))
        bank_doc.is_published = planning.normalize_flag(data.get("is_published"))

        if bank_doc.is_new():
            bank_doc.insert(ignore_permissions=True)
        else:
            bank_doc.save(ignore_permissions=True)

        question_rows = _normalize_rows_payload(
            data.get("questions_json") or data.get("questions"),
            label=_("Questions"),
        )
        question_count = len(question_rows)
        _sync_question_bank_questions(bank_doc.name, question_rows)

        return {
            "quiz_question_bank": bank_doc.name,
            "course": bank_doc.course,
            "is_published": int(bank_doc.is_published or 0),
        }
    except Exception:
        status = "error"
        raise
    finally:
        _log_quiz_event(
            "quiz_question_bank_save",
            started_at=started_at,
            status=status,
            course_plan=course_plan,
            quiz_question_bank=question_bank_name,
            question_count=question_count,
        )


@frappe.whitelist()
def open_session(task_delivery: str):
    student = _require_student_scope(task_delivery)
    payload = quiz_service.open_quiz_session(task_delivery=task_delivery, student=student, user=frappe.session.user)
    _set_quiz_runtime_no_store_headers()
    return payload


@frappe.whitelist()
def save_attempt(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    attempt = (data.get("attempt") or data.get("attempt_id") or "").strip()
    if not attempt:
        frappe.throw(_("Quiz Attempt is required."))
    student = _require_student_for_attempt(attempt)
    responses = data.get("responses") or []
    result = quiz_service.save_attempt_responses(attempt=attempt, responses=responses, student=student)
    _set_quiz_runtime_no_store_headers()
    return result


@frappe.whitelist()
def submit_attempt(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    attempt = (data.get("attempt") or data.get("attempt_id") or "").strip()
    if not attempt:
        frappe.throw(_("Quiz Attempt is required."))
    student = _require_student_for_attempt(attempt)
    responses = data.get("responses") or []
    result = quiz_service.submit_attempt(
        attempt=attempt,
        responses=responses,
        student=student,
        user=frappe.session.user,
    )
    _set_quiz_runtime_no_store_headers()
    return result


def _normalize_payload(payload, kwargs):
    data = payload if payload is not None else kwargs
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw(_("Payload must be a dict."))
    return data


def _set_quiz_runtime_no_store_headers() -> None:
    if not hasattr(frappe, "local") or frappe.local is None:
        frappe.local = SimpleNamespace()

    if not hasattr(frappe.local, "response") or frappe.local.response is None:
        frappe.local.response = {}

    headers = frappe.local.response.get("headers")
    if not isinstance(headers, dict):
        headers = {}
        frappe.local.response["headers"] = headers

    headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    headers["Pragma"] = "no-cache"
    headers["Expires"] = "0"


def _normalize_rows_payload(value, *, label: str) -> list[dict]:
    if value in (None, ""):
        return []
    rows = frappe.parse_json(value) if isinstance(value, str) else value
    if not isinstance(rows, list):
        frappe.throw(_("{label} must be a list.").format(label=label))
    normalized: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            frappe.throw(_("{label} rows must be objects.").format(label=label))
        normalized.append(row)
    return normalized


def _normalize_question_options(question_type: str, rows) -> list[dict]:
    options: list[dict] = []
    for row in _normalize_rows_payload(rows, label=_("Options")):
        option_text = planning.normalize_long_text(row.get("option_text"))
        if not option_text:
            continue
        options.append(
            {
                "option_text": option_text,
                "is_correct": planning.normalize_flag(row.get("is_correct")),
            }
        )
    if question_type == "True / False" and not options:
        options = [
            {"option_text": "True", "is_correct": 1},
            {"option_text": "False", "is_correct": 0},
        ]
    return options


def _sync_question_bank_questions(question_bank: str, rows: list[dict]) -> None:
    existing_names = set(
        frappe.get_all(
            "Quiz Question",
            filters={"question_bank": question_bank},
            pluck="name",
            limit=0,
        )
    )
    retained: set[str] = set()

    for row in rows:
        question_name = planning.normalize_text(row.get("quiz_question") or row.get("question") or row.get("name"))
        if question_name:
            doc = frappe.get_doc("Quiz Question", question_name)
            if planning.normalize_text(doc.question_bank) != question_bank:
                frappe.throw(_("Quiz question does not belong to the selected bank."), frappe.PermissionError)
        else:
            doc = frappe.new_doc("Quiz Question")
            doc.question_bank = question_bank

        doc.title = planning.normalize_text(row.get("title"))
        doc.question_type = planning.normalize_text(row.get("question_type"))
        doc.is_published = planning.normalize_flag(row.get("is_published"))
        doc.prompt = planning.normalize_rich_text(row.get("prompt"))
        doc.accepted_answers = planning.normalize_long_text(row.get("accepted_answers"))
        doc.explanation = planning.normalize_rich_text(row.get("explanation"))
        doc.set("options", _normalize_question_options(doc.question_type, row.get("options")))

        if doc.is_new():
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)
        retained.add(doc.name)

    stale_names = existing_names - retained
    for question_name in stale_names:
        if frappe.db.exists("Quiz Attempt Item", {"quiz_question": question_name}):
            frappe.throw(
                _("This quiz question has already been used in student attempts. Unpublish it instead of removing it."),
                frappe.ValidationError,
            )
        frappe.delete_doc("Quiz Question", question_name, ignore_permissions=True)


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


def _require_course_plan_write_access(course_plan: str, *, expected_course: str | None = None) -> dict:
    course_plan_name = planning.normalize_text(course_plan)
    if not course_plan_name:
        frappe.throw(_("Course Plan is required."))
    course_row = planning.get_course_plan_row(course_plan_name)
    planning.assert_can_manage_course_curriculum(
        frappe.session.user,
        course_row.get("course"),
        frappe.get_roles(frappe.session.user) or [],
        action_label=_("manage quiz banks for this course"),
    )
    expected_course_name = planning.normalize_text(expected_course)
    if expected_course_name and planning.normalize_text(course_row.get("course")) != expected_course_name:
        frappe.throw(_("Course Plan does not govern this quiz question bank."), frappe.PermissionError)
    return course_row


def _question_bank_record_modified(question_bank: str) -> str:
    bank_row = (
        frappe.db.get_value(
            "Quiz Question Bank",
            question_bank,
            ["modified"],
            as_dict=True,
        )
        or {}
    )
    question_rows = frappe.get_all(
        "Quiz Question",
        filters={"question_bank": question_bank},
        fields=["name", "modified"],
        order_by="name asc",
        limit=0,
    )

    digest = hashlib.sha256()
    digest.update(planning.normalize_record_modified(bank_row.get("modified")).encode("utf-8"))
    for row in sorted(
        question_rows or [],
        key=lambda item: (
            planning.normalize_text(item.get("name")),
            planning.normalize_record_modified(item.get("modified")),
        ),
    ):
        digest.update(b"|")
        digest.update(planning.normalize_text(row.get("name")).encode("utf-8"))
        digest.update(b":")
        digest.update(planning.normalize_record_modified(row.get("modified")).encode("utf-8"))
    return digest.hexdigest()


def _log_quiz_event(event: str, *, started_at: float | None = None, **context) -> None:
    logger_factory = getattr(frappe, "logger", None)
    if not callable(logger_factory):
        return

    payload = {"event": planning.normalize_text(event) or "quiz_event"}
    if started_at is not None:
        payload["elapsed_ms"] = round((perf_counter() - started_at) * 1000, 2)
    for key, value in context.items():
        if value in (None, ""):
            continue
        payload[key] = value

    try:
        logger_factory("ifitwala.curriculum").info(payload)
    except Exception:
        return
