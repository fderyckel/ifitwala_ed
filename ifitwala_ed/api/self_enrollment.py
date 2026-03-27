# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from ifitwala_ed.api.activity_booking import _guardian_student_names, _parse_name_list, _student_rows
from ifitwala_ed.api.courses import _require_student_name_for_session_user
from ifitwala_ed.schedule.program_enrollment_request_choice import (
    get_program_enrollment_request_choice_state,
    store_program_enrollment_request_choices,
)


def _resolve_self_enrollment_actor(students=None) -> tuple[str, list[dict]]:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to continue."), frappe.PermissionError)

    requested = _parse_name_list(students, dict_key="student")
    roles = set(frappe.get_roles(user))

    if "Student" in roles:
        student_name = _require_student_name_for_session_user()
        if requested and student_name not in requested:
            frappe.throw(_("You are not permitted to access selected students."), frappe.PermissionError)
        return "Student", _student_rows([student_name])

    guardian = frappe.db.get_value("Guardian", {"user": user}, "name")
    if guardian:
        allowed = _guardian_student_names(guardian)
        if requested:
            allowed_set = set(allowed)
            allowed = [name for name in requested if name in allowed_set]
        return "Guardian", _student_rows(allowed)

    frappe.throw(_("You are not permitted to access course selection."), frappe.PermissionError)


def _window_open_state(window: dict[str, Any]) -> dict[str, Any]:
    status = (window.get("status") or "Draft").strip() or "Draft"
    now_dt = now_datetime()
    open_from = get_datetime(window.get("open_from")) if window.get("open_from") else None
    due_on = get_datetime(window.get("due_on")) if window.get("due_on") else None

    is_open_now = status == "Open"
    if is_open_now and open_from and now_dt < open_from:
        is_open_now = False
    if is_open_now and due_on and now_dt > due_on:
        is_open_now = False

    return {
        "status": status,
        "open_from": window.get("open_from"),
        "due_on": window.get("due_on"),
        "is_open_now": 1 if is_open_now else 0,
    }


def _locked_reason(*, window: dict[str, Any], request_row: dict | None) -> str | None:
    open_state = _window_open_state(window)
    request_status = ((request_row or {}).get("status") or "").strip()
    request_validation_status = ((request_row or {}).get("validation_status") or "").strip()
    if request_status and request_status != "Draft":
        if request_validation_status == "Invalid":
            return _(
                "Selection has already been submitted and is now read-only. The school needs to review it because some choices still need attention."
            )
        if request_status == "Approved":
            return _("Selection has already been confirmed and is now read-only.")
        return _("Selection has already been submitted and is now read-only.")
    if (window.get("status") or "Draft").strip() != "Open":
        return _("Course selection window is not open.")

    now_dt = now_datetime()
    open_from = get_datetime(window.get("open_from")) if window.get("open_from") else None
    due_on = get_datetime(window.get("due_on")) if window.get("due_on") else None
    if open_from and now_dt < open_from:
        return _("Course selection opens on {0}.").format(open_from)
    if due_on and now_dt > due_on:
        return _("Course selection closed on {0}.").format(due_on)
    if open_state.get("is_open_now") != 1:
        return _("Course selection is not available right now.")
    return None


def _request_rows_by_name(request_names: list[str]) -> dict[str, dict]:
    names = sorted({(name or "").strip() for name in (request_names or []) if (name or "").strip()})
    if not names:
        return {}
    rows = frappe.get_all(
        "Program Enrollment Request",
        filters={"name": ["in", names]},
        fields=[
            "name",
            "student",
            "program_offering",
            "academic_year",
            "selection_window",
            "status",
            "validation_status",
            "submitted_on",
            "submitted_by",
        ],
        limit=max(50, len(names) + 20),
    )
    return {(row.get("name") or "").strip(): row for row in rows or [] if (row.get("name") or "").strip()}


def _window_rows(window_names: list[str], *, audience: str) -> list[dict]:
    names = sorted({(name or "").strip() for name in (window_names or []) if (name or "").strip()})
    if not names:
        return []
    return frappe.get_all(
        "Program Offering Selection Window",
        filters={"name": ["in", names], "audience": audience},
        fields=[
            "name",
            "program_offering",
            "program",
            "school",
            "academic_year",
            "audience",
            "status",
            "open_from",
            "due_on",
            "instructions",
        ],
        order_by="modified desc",
        limit=max(50, len(names) + 20),
    )


def _offering_context(offering_names: list[str]) -> dict[str, dict]:
    names = sorted({(name or "").strip() for name in (offering_names or []) if (name or "").strip()})
    if not names:
        return {}
    rows = frappe.get_all(
        "Program Offering",
        filters={"name": ["in", names]},
        fields=["name", "offering_title", "program", "school"],
        limit=max(50, len(names) + 20),
    )
    return {(row.get("name") or "").strip(): row for row in rows or [] if (row.get("name") or "").strip()}


def _program_map(program_names: list[str]) -> dict[str, dict]:
    names = sorted({(name or "").strip() for name in (program_names or []) if (name or "").strip()})
    if not names:
        return {}
    rows = frappe.get_all(
        "Program",
        filters={"name": ["in", names]},
        fields=["name", "program_name", "program_abbreviation"],
        limit=max(50, len(names) + 20),
    )
    return {(row.get("name") or "").strip(): row for row in rows or [] if (row.get("name") or "").strip()}


def _school_map(school_names: list[str]) -> dict[str, dict]:
    names = sorted({(name or "").strip() for name in (school_names or []) if (name or "").strip()})
    if not names:
        return {}
    rows = frappe.get_all(
        "School",
        filters={"name": ["in", names]},
        fields=["name", "school_name", "abbr"],
        limit=max(50, len(names) + 20),
    )
    return {(row.get("name") or "").strip(): row for row in rows or [] if (row.get("name") or "").strip()}


def _board_window_payload(
    *,
    actor_type: str,
    student_rows: list[dict],
    include_closed: int,
) -> list[dict]:
    student_map = {
        (row.get("student") or "").strip(): row for row in student_rows or [] if (row.get("student") or "").strip()
    }
    student_names = list(student_map.keys())
    if not student_names:
        return []

    selection_rows = frappe.get_all(
        "Program Offering Selection Window Student",
        filters={"student": ["in", student_names]},
        fields=[
            "parent as selection_window",
            "student",
            "student_name",
            "student_cohort",
            "program_enrollment_request",
        ],
        order_by="parent asc, idx asc",
        limit=max(100, len(student_names) * 20),
    )
    if not selection_rows:
        return []

    window_names = [row.get("selection_window") for row in selection_rows if row.get("selection_window")]
    windows = _window_rows(window_names, audience=actor_type)
    if not windows:
        return []

    window_map = {(row.get("name") or "").strip(): row for row in windows if (row.get("name") or "").strip()}
    request_names = [
        row.get("program_enrollment_request") for row in selection_rows if row.get("program_enrollment_request")
    ]
    request_map = _request_rows_by_name(request_names)
    offering_map = _offering_context([row.get("program_offering") for row in windows if row.get("program_offering")])
    program_map = _program_map([row.get("program") for row in windows if row.get("program")])
    school_map = _school_map([row.get("school") for row in windows if row.get("school")])

    grouped: dict[str, list[dict]] = {}
    for row in selection_rows or []:
        window_name = (row.get("selection_window") or "").strip()
        student = (row.get("student") or "").strip()
        if not window_name or window_name not in window_map or student not in student_map:
            continue
        grouped.setdefault(window_name, []).append(row)

    payload = []
    for window_name, rows in grouped.items():
        window = window_map[window_name]
        open_state = _window_open_state(window)
        offering = offering_map.get((window.get("program_offering") or "").strip()) or {}
        program = program_map.get((window.get("program") or "").strip()) or {}
        school = school_map.get((window.get("school") or "").strip()) or {}

        students_payload = []
        submitted_count = 0
        invalid_count = 0
        approved_count = 0

        for row in rows:
            student_name = (row.get("student") or "").strip()
            student_meta = student_map.get(student_name) or {}
            request_row = request_map.get((row.get("program_enrollment_request") or "").strip()) or None
            if request_row and (request_row.get("status") or "").strip() != "Draft":
                submitted_count += 1
            if request_row and (request_row.get("validation_status") or "").strip() == "Invalid":
                invalid_count += 1
            if request_row and (request_row.get("status") or "").strip() == "Approved":
                approved_count += 1

            locked_reason = _locked_reason(window=window, request_row=request_row)
            students_payload.append(
                {
                    **student_meta,
                    "student": student_name,
                    "request": {
                        "name": (request_row or {}).get("name"),
                        "status": ((request_row or {}).get("status") or "Draft").strip() or "Draft",
                        "validation_status": ((request_row or {}).get("validation_status") or "Not Validated").strip()
                        or "Not Validated",
                        "submitted_on": (request_row or {}).get("submitted_on"),
                        "submitted_by": (request_row or {}).get("submitted_by"),
                        "can_edit": 0 if locked_reason else 1,
                        "locked_reason": locked_reason,
                    }
                    if request_row
                    else None,
                }
            )

        window_status = (window.get("status") or "").strip() or "Draft"
        is_visible = bool(cint(include_closed or 0) == 1 or window_status in {"Open", "Closed"} or submitted_count > 0)
        if not is_visible:
            continue

        payload.append(
            {
                "selection_window": window_name,
                "program_offering": window.get("program_offering"),
                "program": window.get("program"),
                "program_label": (program.get("program_name") or "").strip() or window.get("program"),
                "program_abbreviation": program.get("program_abbreviation"),
                "school": window.get("school"),
                "school_label": (school.get("school_name") or "").strip() or window.get("school"),
                "school_abbr": school.get("abbr"),
                "title": (offering.get("offering_title") or "").strip()
                or (program.get("program_name") or "").strip()
                or window.get("program_offering"),
                "academic_year": window.get("academic_year"),
                "audience": window.get("audience"),
                "status": open_state["status"],
                "open_from": open_state["open_from"],
                "due_on": open_state["due_on"],
                "is_open_now": open_state["is_open_now"],
                "instructions": window.get("instructions"),
                "summary": {
                    "total_students": len(rows),
                    "submitted_count": submitted_count,
                    "pending_count": max(len(rows) - submitted_count, 0),
                    "invalid_count": invalid_count,
                    "approved_count": approved_count,
                },
                "students": students_payload,
            }
        )

    return sorted(
        payload,
        key=lambda row: (
            -int(row.get("is_open_now") or 0),
            row.get("due_on") or "",
            row.get("title") or "",
            row.get("selection_window") or "",
        ),
    )


def _resolve_window_student_request(selection_window: str, student: str | None = None) -> tuple[str, dict, dict, dict]:
    actor_type, students = _resolve_self_enrollment_actor(students=[student] if student else None)
    if not students:
        frappe.throw(_("No authorized student was found for this selection window."), frappe.PermissionError)

    student_meta = students[0]
    student_name = (student_meta.get("student") or "").strip()
    if not student_name:
        frappe.throw(_("No authorized student was found for this selection window."), frappe.PermissionError)

    window_rows = _window_rows([selection_window], audience=actor_type)
    if not window_rows:
        frappe.throw(_("You do not have access to this course selection window."), frappe.PermissionError)
    window = window_rows[0]

    selection_row = frappe.get_all(
        "Program Offering Selection Window Student",
        filters={"parent": selection_window, "student": student_name},
        fields=["program_enrollment_request"],
        limit=1,
    )
    if not selection_row:
        frappe.throw(_("You do not have access to this course selection window."), frappe.PermissionError)

    request_name = (selection_row[0].get("program_enrollment_request") or "").strip()
    if not request_name:
        frappe.throw(_("This selection window has not prepared a Program Enrollment Request for the student yet."))

    request = frappe.get_doc("Program Enrollment Request", request_name)
    if (request.selection_window or "").strip() and (request.selection_window or "").strip() != selection_window:
        frappe.throw(
            _("This Program Enrollment Request does not belong to the selected window."), frappe.PermissionError
        )

    return actor_type, student_meta, window, request


def _build_choice_state_response(*, actor_type: str, student_meta: dict, window: dict, request) -> dict:
    locked_reason = _locked_reason(
        window=window,
        request_row={
            "status": request.status,
            "validation_status": request.validation_status,
            "submitted_on": request.submitted_on,
            "submitted_by": request.submitted_by,
        },
    )
    can_edit = locked_reason is None
    choice_state = get_program_enrollment_request_choice_state(request, can_edit=can_edit)

    offering = (
        frappe.db.get_value(
            "Program Offering",
            window.get("program_offering"),
            ["offering_title", "program", "school"],
            as_dict=True,
        )
        or {}
    )
    program = (
        frappe.db.get_value(
            "Program",
            window.get("program"),
            ["program_name", "program_abbreviation"],
            as_dict=True,
        )
        or {}
    )
    school = frappe.db.get_value("School", window.get("school"), ["school_name", "abbr"], as_dict=True) or {}

    return {
        "generated_at": now_datetime(),
        "viewer": {
            "actor_type": actor_type,
            "user": frappe.session.user,
        },
        "window": {
            "selection_window": window.get("name"),
            "program_offering": window.get("program_offering"),
            "title": (offering.get("offering_title") or "").strip()
            or (program.get("program_name") or "").strip()
            or window.get("program_offering"),
            "program": window.get("program"),
            "program_label": (program.get("program_name") or "").strip() or window.get("program"),
            "program_abbreviation": program.get("program_abbreviation"),
            "school": window.get("school"),
            "school_label": (school.get("school_name") or "").strip() or window.get("school"),
            "school_abbr": school.get("abbr"),
            "academic_year": window.get("academic_year"),
            "status": window.get("status"),
            "open_from": window.get("open_from"),
            "due_on": window.get("due_on"),
            "is_open_now": _window_open_state(window)["is_open_now"],
            "instructions": window.get("instructions"),
        },
        "student": student_meta,
        "permissions": {
            "can_edit": 0 if locked_reason else 1,
            "can_submit": 0 if locked_reason else 1,
            "locked_reason": locked_reason,
        },
        **choice_state,
    }


def _submit_block_message(choice_state: dict) -> str:
    reasons = [
        str(message or "").strip()
        for message in list(((choice_state.get("validation") or {}).get("reasons") or []))
        if str(message or "").strip()
    ]
    if not reasons:
        return _("Please review the course choices above before submitting.")
    if len(reasons) == 1:
        return reasons[0]
    return _("Please review the course choices before submitting: {0}").format("; ".join(reasons[:3]))


def _parse_course_rows(courses) -> list[dict]:
    if isinstance(courses, str):
        text = courses.strip()
        return frappe.parse_json(text) if text else []
    if courses is None:
        return []
    if not isinstance(courses, list):
        frappe.throw(_("Courses must be a JSON list."))
    return courses


@frappe.whitelist()
def get_self_enrollment_portal_board(students=None, include_closed: int = 0):
    actor_type, student_rows = _resolve_self_enrollment_actor(students=students)
    return {
        "generated_at": now_datetime(),
        "viewer": {
            "actor_type": actor_type,
            "user": frappe.session.user,
        },
        "students": student_rows,
        "windows": _board_window_payload(
            actor_type=actor_type,
            student_rows=student_rows,
            include_closed=cint(include_closed or 0),
        ),
    }


@frappe.whitelist()
def get_self_enrollment_choice_state(selection_window: str, student: str | None = None):
    actor_type, student_meta, window, request = _resolve_window_student_request(selection_window, student)
    return _build_choice_state_response(
        actor_type=actor_type,
        student_meta=student_meta,
        window={**window, "name": selection_window},
        request=request,
    )


@frappe.whitelist()
def save_self_enrollment_choices(selection_window: str, courses=None, student: str | None = None):
    actor_type, student_meta, window, request = _resolve_window_student_request(selection_window, student)
    locked_reason = _locked_reason(window=window, request_row={"status": request.status})
    if locked_reason:
        frappe.throw(locked_reason)

    store_program_enrollment_request_choices(request, courses=_parse_course_rows(courses))
    request.save(ignore_permissions=True)
    request.reload()
    return _build_choice_state_response(
        actor_type=actor_type,
        student_meta=student_meta,
        window={**window, "name": selection_window},
        request=request,
    )


@frappe.whitelist()
def submit_self_enrollment_choices(selection_window: str, courses=None, student: str | None = None):
    actor_type, student_meta, window, request = _resolve_window_student_request(selection_window, student)
    if (request.status or "").strip() == "Submitted":
        return _build_choice_state_response(
            actor_type=actor_type,
            student_meta=student_meta,
            window={**window, "name": selection_window},
            request=request,
        )

    locked_reason = _locked_reason(window=window, request_row={"status": request.status})
    if locked_reason:
        frappe.throw(locked_reason)

    store_program_enrollment_request_choices(request, courses=_parse_course_rows(courses))
    live_choice_state = get_program_enrollment_request_choice_state(request, can_edit=True)
    if not bool((live_choice_state.get("summary") or {}).get("ready_for_submit")):
        frappe.throw(_submit_block_message(live_choice_state))

    request.status = "Submitted"
    request.submitted_on = now_datetime()
    request.submitted_by = frappe.session.user
    request.save(ignore_permissions=True)
    request.reload()
    return _build_choice_state_response(
        actor_type=actor_type,
        student_meta=student_meta,
        window={**window, "name": selection_window},
        request=request,
    )
