# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.schedule.basket_group_utils import get_offering_course_semantics
from ifitwala_ed.schedule.program_enrollment_request_choice import get_program_enrollment_request_choice_state
from ifitwala_ed.school_settings.school_settings_utils import get_allowed_schools

VIEW_MODE_MATRIX = "Student x Course Matrix"
VIEW_MODE_SUMMARY = "Course Demand Summary"
VIEW_MODE_WINDOW_TRACKER = "Selection Window Tracker"
DEFAULT_REQUEST_KIND = "Academic"
DETAIL_MESSAGE_LIMIT = 4

STATUS_ORDER = ["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Cancelled"]
VALIDATION_STATUS_ORDER = ["Not Validated", "Valid", "Invalid"]
SUBMISSION_STATUS_SUBMITTED = "Submitted"
SUBMISSION_STATUS_NOT_SUBMITTED = "Not Submitted"
SUBMISSION_STATUS_MISSING_REQUEST = "Missing Request"
CURRENT_STATE_READY = "Ready to Submit"
CURRENT_STATE_BLOCKED = "Blocked"
PROBLEM_STATUS_SELECTION_BLOCKED = "Selection Blocked"
PROBLEM_STATUS_INVALID_REQUEST = "Invalid Request"
PROBLEM_STATUS_NEEDS_OVERRIDE = "Needs Override"
PROBLEM_STATUS_MISSING_REQUEST = "Missing Request"
INVALID_REASON_BUCKETS = [
    "Prerequisite",
    "Capacity Full",
    "Basket Missing Required",
    "Basket Group Not Selected",
    "Basket Group Coverage",
    "Repeat / Max Attempts",
    "Course Not In Offering",
    "Rule Misconfigured / Unsupported",
    "Other",
]


def execute(filters=None):
    filters, requests, window_rows = get_filtered_requests(
        filters, require_matrix_offering=True, include_window_rows=True
    )
    if filters.get("view_mode") == VIEW_MODE_WINDOW_TRACKER:
        columns, data = _build_window_tracker_view(window_rows, requests, filters)
        chart = _build_window_submission_chart(data)
        report_summary = _build_window_tracker_summary(data)
        return columns, data, None, chart, report_summary

    course_catalog = _resolve_course_catalog(requests, filters)
    if filters.get("view_mode") == VIEW_MODE_MATRIX:
        columns, data = _build_matrix_view(requests, course_catalog)
        chart = _build_request_status_chart(requests)
    else:
        columns, data = _build_summary_view(requests, course_catalog)
        chart = _build_course_demand_chart(data)

    report_summary = _build_report_summary(requests)
    return columns, data, None, chart, report_summary


def get_filtered_requests(filters=None, *, require_matrix_offering=True, include_window_rows=False):
    filters = _normalize_filters(filters or {}, require_matrix_offering=require_matrix_offering)

    allowed_schools = get_allowed_schools(frappe.session.user, filters.get("school"))
    if not allowed_schools:
        frappe.throw(_("You do not have access to the selected school."))

    window_rows = _fetch_window_student_rows(filters, allowed_schools)
    tracker_request_names = (
        [row.get("program_enrollment_request") for row in window_rows if row.get("program_enrollment_request")]
        if filters.get("view_mode") == VIEW_MODE_WINDOW_TRACKER
        else None
    )

    request_rows = _fetch_request_rows(filters, allowed_schools, request_names=tracker_request_names)
    request_rows = _dedupe_request_rows(request_rows, latest_only=filters.get("latest_request_only"))

    course_rows_by_parent = _fetch_course_rows_by_parent([row["name"] for row in request_rows])
    requests = _build_request_models(request_rows, course_rows_by_parent)
    if filters.get("view_mode") != VIEW_MODE_WINDOW_TRACKER:
        requests = _apply_post_dedupe_filters(requests, filters)
    if include_window_rows:
        return filters, requests, window_rows
    return filters, requests


def _normalize_filters(filters, *, require_matrix_offering=True):
    filters = frappe._dict(filters or {})
    filters["view_mode"] = (filters.get("view_mode") or VIEW_MODE_MATRIX).strip() or VIEW_MODE_MATRIX
    if filters["view_mode"] not in {VIEW_MODE_MATRIX, VIEW_MODE_SUMMARY, VIEW_MODE_WINDOW_TRACKER}:
        filters["view_mode"] = VIEW_MODE_MATRIX

    filters["school"] = (filters.get("school") or "").strip()
    filters["academic_year"] = (filters.get("academic_year") or "").strip()
    filters["program"] = (filters.get("program") or "").strip()
    filters["program_offering"] = (filters.get("program_offering") or "").strip()
    filters["selection_window"] = (filters.get("selection_window") or "").strip()
    filters["request_kind"] = (filters.get("request_kind") or DEFAULT_REQUEST_KIND).strip() or DEFAULT_REQUEST_KIND
    filters["request_status"] = (filters.get("request_status") or "").strip()
    filters["validation_status"] = (filters.get("validation_status") or "").strip()
    filters["invalid_reason_bucket"] = (filters.get("invalid_reason_bucket") or "").strip()
    filters["latest_request_only"] = cint(filters.get("latest_request_only", 1)) == 1
    filters["requires_override"] = cint(filters.get("requires_override") or 0) == 1

    if not filters["school"]:
        frappe.throw(_("School is required."))
    if not filters["academic_year"]:
        frappe.throw(_("Academic Year is required."))
    if require_matrix_offering and filters["view_mode"] == VIEW_MODE_MATRIX and not filters["program_offering"]:
        frappe.throw(_("Program Offering is required for Student x Course Matrix view."))
    if filters["view_mode"] == VIEW_MODE_WINDOW_TRACKER and not filters["selection_window"]:
        frappe.throw(_("Selection Window is required for Selection Window Tracker view."))

    if filters["request_status"] and filters["request_status"] not in STATUS_ORDER:
        filters["request_status"] = ""
    if filters["validation_status"] and filters["validation_status"] not in VALIDATION_STATUS_ORDER:
        filters["validation_status"] = ""
    if filters["invalid_reason_bucket"] and filters["invalid_reason_bucket"] not in INVALID_REASON_BUCKETS:
        filters["invalid_reason_bucket"] = ""

    return filters


def _fetch_request_rows(filters, allowed_schools, request_names=None):
    names = sorted({(name or "").strip() for name in (request_names or []) if (name or "").strip()})
    if request_names is not None and not names:
        return []

    conditions = [
        "per.school IN %(allowed_schools)s",
        "per.academic_year = %(academic_year)s",
        "IFNULL(per.student, '') != ''",
    ]
    params = {
        "allowed_schools": tuple(allowed_schools),
        "academic_year": filters.get("academic_year"),
    }

    if filters.get("program"):
        conditions.append("per.program = %(program)s")
        params["program"] = filters.get("program")
    if filters.get("program_offering"):
        conditions.append("per.program_offering = %(program_offering)s")
        params["program_offering"] = filters.get("program_offering")
    if filters.get("selection_window") and not names:
        conditions.append("per.selection_window = %(selection_window)s")
        params["selection_window"] = filters.get("selection_window")
    if filters.get("request_kind"):
        conditions.append("per.request_kind = %(request_kind)s")
        params["request_kind"] = filters.get("request_kind")
    if names:
        conditions.append("per.name IN %(request_names)s")
        params["request_names"] = tuple(names)

    where = " AND ".join(conditions)
    return frappe.db.sql(
        f"""
        SELECT
            per.name,
            per.student,
            st.student_full_name,
            st.student_preferred_name,
            per.program_offering,
            per.program,
            per.school,
            per.academic_year,
            per.request_kind,
            per.status,
            per.validation_status,
            per.validation_payload,
            per.requires_override,
            per.override_approved,
            per.override_reason,
            per.selection_window,
            per.submitted_on,
            per.modified
        FROM `tabProgram Enrollment Request` per
        LEFT JOIN `tabStudent` st
            ON st.name = per.student
        WHERE {where}
        ORDER BY per.modified DESC, per.name DESC
        """,
        params,
        as_dict=True,
    )


def _fetch_window_student_rows(filters, allowed_schools):
    selection_window = (filters.get("selection_window") or "").strip()
    if not selection_window:
        return []

    return frappe.db.sql(
        """
        SELECT
            w.name AS selection_window,
            w.status AS window_status,
            w.open_from,
            w.due_on,
            w.program_offering,
            w.program,
            w.school,
            w.academic_year,
            ws.student,
            COALESCE(NULLIF(ws.student_name, ''), st.student_full_name, ws.student) AS student_name,
            ws.student_cohort,
            ws.source_program_enrollment,
            ws.program_enrollment_request
        FROM `tabProgram Offering Selection Window` w
        INNER JOIN `tabProgram Offering Selection Window Student` ws
            ON ws.parent = w.name
           AND ws.parenttype = 'Program Offering Selection Window'
        LEFT JOIN `tabStudent` st
            ON st.name = ws.student
        WHERE w.name = %(selection_window)s
          AND w.school IN %(allowed_schools)s
        ORDER BY COALESCE(NULLIF(ws.student_name, ''), st.student_full_name, ws.student) ASC, ws.student ASC
        """,
        {
            "selection_window": selection_window,
            "allowed_schools": tuple(allowed_schools),
        },
        as_dict=True,
    )


def _dedupe_request_rows(rows, *, latest_only):
    if not latest_only:
        return rows

    output = []
    seen = set()
    for row in rows or []:
        key = (
            (row.get("student") or "").strip(),
            (row.get("program_offering") or "").strip(),
            (row.get("academic_year") or "").strip(),
            (row.get("request_kind") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def _fetch_course_rows_by_parent(request_names):
    names = [(name or "").strip() for name in (request_names or []) if (name or "").strip()]
    if not names:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            parent,
            idx,
            course,
            course_name,
            required,
            applied_basket_group,
            choice_rank,
            status
        FROM `tabProgram Enrollment Request Course`
        WHERE parent IN %(parents)s
        ORDER BY parent ASC, idx ASC
        """,
        {"parents": tuple(names)},
        as_dict=True,
    )

    grouped = {}
    for row in rows or []:
        grouped.setdefault(row.get("parent"), []).append(row)
    return grouped


def _build_request_models(request_rows, course_rows_by_parent):
    requests = []
    for row in request_rows or []:
        course_rows = []
        seen_courses = set()
        for course_row in course_rows_by_parent.get(row.get("name"), []) or []:
            course = (course_row.get("course") or "").strip()
            if not course or course in seen_courses:
                continue
            seen_courses.add(course)
            course_rows.append(
                {
                    "course": course,
                    "course_name": (course_row.get("course_name") or "").strip(),
                    "required": 1 if cint(course_row.get("required")) == 1 else 0,
                    "applied_basket_group": (course_row.get("applied_basket_group") or "").strip(),
                    "choice_rank": course_row.get("choice_rank"),
                    "status": (course_row.get("status") or "").strip() or "Requested",
                }
            )

        invalid_reason_info = _extract_invalid_reason_info(row)
        requests.append(
            {
                "name": row.get("name"),
                "student": row.get("student"),
                "student_name": _build_student_label(row),
                "program_offering": row.get("program_offering"),
                "program": row.get("program"),
                "school": row.get("school"),
                "academic_year": row.get("academic_year"),
                "request_kind": row.get("request_kind"),
                "selection_window": row.get("selection_window"),
                "request_status": row.get("status"),
                "validation_status": row.get("validation_status"),
                "requires_override": 1 if cint(row.get("requires_override")) == 1 else 0,
                "override_approved": 1 if cint(row.get("override_approved")) == 1 else 0,
                "override_reason": (row.get("override_reason") or "").strip(),
                "submitted_on": row.get("submitted_on"),
                "modified": row.get("modified"),
                "courses": course_rows,
                "course_count": len(course_rows),
                "invalid_reason_buckets": invalid_reason_info["buckets"],
                "invalid_reason_summary": invalid_reason_info["summary"],
                "invalid_reason_detail": invalid_reason_info["detail"],
            }
        )
    return requests


def _build_student_label(row):
    full_name = (row.get("student_full_name") or "").strip()
    preferred_name = (row.get("student_preferred_name") or "").strip()
    if full_name and preferred_name and preferred_name != full_name:
        return f"{full_name} ({preferred_name})"
    return full_name or (row.get("student") or "")


def _apply_post_dedupe_filters(requests, filters):
    output = []
    for request in requests or []:
        if filters.get("request_status") and request.get("request_status") != filters.get("request_status"):
            continue
        if filters.get("validation_status") and request.get("validation_status") != filters.get("validation_status"):
            continue
        if filters.get("requires_override") and cint(request.get("requires_override")) != 1:
            continue
        if filters.get("invalid_reason_bucket") and filters.get("invalid_reason_bucket") not in (
            request.get("invalid_reason_buckets") or []
        ):
            continue
        output.append(request)
    return output


def _resolve_course_catalog(requests, filters):
    ordered = []
    seen = set()
    labels = {}
    required_map = {}

    if filters.get("program_offering"):
        for course, semantics in (get_offering_course_semantics(filters.get("program_offering")) or {}).items():
            course_name = (semantics.get("course_name") or "").strip()
            ordered.append(course)
            seen.add(course)
            labels[course] = course_name
            required_map[course] = 1 if cint(semantics.get("required")) == 1 else 0

    extras = {}
    for request in requests or []:
        for course_row in request.get("courses") or []:
            course = (course_row.get("course") or "").strip()
            if not course:
                continue
            labels.setdefault(course, (course_row.get("course_name") or "").strip())
            required_map[course] = 1 if required_map.get(course) or cint(course_row.get("required")) == 1 else 0
            if course not in seen:
                extras[course] = labels.get(course) or course

    for course in sorted(extras, key=lambda item: (extras[item] or item, item)):
        ordered.append(course)
        seen.add(course)

    return [
        {
            "course": course,
            "course_name": labels.get(course) or "",
            "required": 1 if required_map.get(course) else 0,
            "fieldname": _course_fieldname(course, idx),
        }
        for idx, course in enumerate(ordered, start=1)
    ]


def _course_fieldname(course, idx):
    return f"course_{idx:03d}_{frappe.scrub(course)[:40]}"


def _build_matrix_view(requests, course_catalog):
    columns = [
        {
            "label": _("Request"),
            "fieldname": "request",
            "fieldtype": "Link",
            "options": "Program Enrollment Request",
            "width": 170,
        },
        {"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 140},
        {"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 220},
        {
            "label": _("Program Offering"),
            "fieldname": "program_offering",
            "fieldtype": "Link",
            "options": "Program Offering",
            "width": 170,
        },
        {"label": _("Request Status"), "fieldname": "request_status", "fieldtype": "Data", "width": 130},
        {"label": _("Validation"), "fieldname": "validation_status", "fieldtype": "Data", "width": 110},
        {"label": _("Needs Override"), "fieldname": "requires_override", "fieldtype": "Check", "width": 120},
        {"label": _("Override Approved"), "fieldname": "override_approved", "fieldtype": "Check", "width": 130},
        {"label": _("Invalid Buckets"), "fieldname": "invalid_reason_summary", "fieldtype": "Data", "width": 220},
        {"label": _("Invalid Detail"), "fieldname": "invalid_reason_detail", "fieldtype": "Data", "width": 320},
        {"label": _("Courses"), "fieldname": "course_count", "fieldtype": "Int", "width": 90},
    ]
    columns.extend(
        [
            {
                "label": meta["course"],
                "fieldname": meta["fieldname"],
                "fieldtype": "Data",
                "width": 110,
            }
            for meta in course_catalog
        ]
    )

    course_field_map = {meta["course"]: meta["fieldname"] for meta in course_catalog}
    data = []
    for request in requests or []:
        row = {
            "request": request.get("name"),
            "student": request.get("student"),
            "student_name": request.get("student_name"),
            "program_offering": request.get("program_offering"),
            "request_status": request.get("request_status"),
            "validation_status": request.get("validation_status"),
            "requires_override": request.get("requires_override"),
            "override_approved": request.get("override_approved"),
            "invalid_reason_summary": request.get("invalid_reason_summary"),
            "invalid_reason_detail": request.get("invalid_reason_detail"),
            "course_count": request.get("course_count"),
        }
        for course_row in request.get("courses") or []:
            fieldname = course_field_map.get(course_row.get("course"))
            if not fieldname:
                continue
            row[fieldname] = _format_matrix_cell(course_row)
        data.append(row)

    data.sort(key=lambda row: (row.get("student_name") or "", row.get("request") or ""))
    return columns, data


def _build_window_tracker_view(window_rows, requests, filters):
    columns = [
        {
            "label": _("Request"),
            "fieldname": "request",
            "fieldtype": "Link",
            "options": "Program Enrollment Request",
            "width": 170,
        },
        {"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 140},
        {"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 220},
        {"label": _("Submission"), "fieldname": "submission_status", "fieldtype": "Data", "width": 130},
        {"label": _("Review Status"), "fieldname": "request_status", "fieldtype": "Data", "width": 130},
        {"label": _("Current State"), "fieldname": "current_state", "fieldtype": "Data", "width": 130},
        {"label": _("Needs Override"), "fieldname": "requires_override", "fieldtype": "Check", "width": 120},
        {"label": _("Problem"), "fieldname": "problem_status", "fieldtype": "Data", "width": 150},
        {"label": _("Problem Detail"), "fieldname": "problem_detail", "fieldtype": "Data", "width": 360},
        {"label": _("Submitted On"), "fieldname": "submitted_on", "fieldtype": "Datetime", "width": 160},
    ]

    requests_by_name = {request.get("name"): request for request in requests or [] if request.get("name")}
    live_choice_states = {}
    data = []

    for window_row in window_rows or []:
        request_name = (window_row.get("program_enrollment_request") or "").strip()
        request = requests_by_name.get(request_name)
        live_choice_state = None
        if request_name and request and (request.get("request_status") or "").strip() == "Draft":
            live_choice_state = live_choice_states.get(request_name)
            if live_choice_state is None:
                live_choice_state = _get_live_choice_state(request_name)
                live_choice_states[request_name] = live_choice_state

        row = _build_window_tracker_row(window_row, request, live_choice_state)
        if _tracker_row_matches_filters(row, filters):
            data.append(row)

    data.sort(key=_window_tracker_sort_key)
    return columns, data


def _build_window_tracker_row(window_row, request, live_choice_state):
    request_status = (request.get("request_status") or "").strip() if request else ""
    problem_status, problem_detail = _window_problem_state(request, live_choice_state)
    return {
        "request": (request.get("name") if request else (window_row.get("program_enrollment_request") or "")).strip(),
        "student": (window_row.get("student") or "").strip(),
        "student_name": (window_row.get("student_name") or "").strip(),
        "submission_status": _window_submission_status(request),
        "request_status": request_status,
        "validation_status": (request.get("validation_status") or "").strip() if request else "",
        "request_kind": (request.get("request_kind") or DEFAULT_REQUEST_KIND).strip()
        if request
        else DEFAULT_REQUEST_KIND,
        "current_state": _window_current_state(request, live_choice_state),
        "requires_override": 1 if request and cint(request.get("requires_override")) == 1 else 0,
        "override_approved": 1 if request and cint(request.get("override_approved")) == 1 else 0,
        "problem_status": problem_status,
        "problem_detail": problem_detail,
        "submitted_on": request.get("submitted_on") if request else None,
        "invalid_reason_buckets": list(request.get("invalid_reason_buckets") or []) if request else [],
    }


def _tracker_row_matches_filters(row, filters):
    if filters.get("request_kind") and row.get("request_kind") != filters.get("request_kind"):
        return False
    if filters.get("request_status") and row.get("request_status") != filters.get("request_status"):
        return False
    if filters.get("validation_status") and row.get("validation_status") != filters.get("validation_status"):
        return False
    if filters.get("requires_override") and cint(row.get("requires_override")) != 1:
        return False
    if filters.get("invalid_reason_bucket") and filters.get("invalid_reason_bucket") not in (
        row.get("invalid_reason_buckets") or []
    ):
        return False
    return True


def _window_tracker_sort_key(row):
    submission_rank = {
        SUBMISSION_STATUS_MISSING_REQUEST: 0,
        SUBMISSION_STATUS_NOT_SUBMITTED: 1,
        SUBMISSION_STATUS_SUBMITTED: 2,
    }
    return (
        0 if row.get("problem_status") else 1,
        submission_rank.get((row.get("submission_status") or "").strip(), 9),
        row.get("student_name") or "",
        row.get("student") or "",
    )


def _window_submission_status(request):
    if not request:
        return SUBMISSION_STATUS_MISSING_REQUEST

    request_status = (request.get("request_status") or "").strip()
    if request.get("submitted_on") or request_status in {"Submitted", "Under Review", "Approved", "Rejected"}:
        return SUBMISSION_STATUS_SUBMITTED
    if request_status == "Cancelled" and request.get("submitted_on"):
        return SUBMISSION_STATUS_SUBMITTED
    return SUBMISSION_STATUS_NOT_SUBMITTED


def _window_current_state(request, live_choice_state):
    if not request:
        return SUBMISSION_STATUS_MISSING_REQUEST

    request_status = (request.get("request_status") or "").strip()
    if request_status == "Draft" and live_choice_state is not None:
        return CURRENT_STATE_READY if live_choice_state.get("ready_for_submit") else CURRENT_STATE_BLOCKED
    return (request.get("validation_status") or "").strip() or _("Not Reviewed")


def _window_problem_state(request, live_choice_state):
    if not request:
        return PROBLEM_STATUS_MISSING_REQUEST, _("Request has not been prepared for this student yet.")

    request_status = (request.get("request_status") or "").strip()
    if request_status == "Draft" and live_choice_state is not None and not live_choice_state.get("ready_for_submit"):
        detail = _compact_messages(live_choice_state.get("reasons") or [])
        return (
            PROBLEM_STATUS_SELECTION_BLOCKED,
            detail or _("The current course choices still need attention before this request can be submitted."),
        )

    if cint(request.get("requires_override")) == 1 and cint(request.get("override_approved")) != 1:
        detail = (
            (request.get("override_reason") or "").strip()
            or request.get("invalid_reason_detail")
            or _("School review is required before this request can advance.")
        )
        return PROBLEM_STATUS_NEEDS_OVERRIDE, detail

    if (request.get("validation_status") or "").strip() == "Invalid":
        return PROBLEM_STATUS_INVALID_REQUEST, request.get("invalid_reason_detail") or _(
            "Request needs academic review."
        )

    return "", ""


def _get_live_choice_state(request_name):
    if not request_name:
        return {"ready_for_submit": False, "reasons": []}

    # Only draft tracker rows compute live blockers; other report modes stay request-snapshot based.
    request = frappe.get_doc("Program Enrollment Request", request_name)
    choice_state = get_program_enrollment_request_choice_state(request, can_edit=False)
    return {
        "ready_for_submit": bool((choice_state.get("summary") or {}).get("ready_for_submit")),
        "reasons": list((choice_state.get("validation") or {}).get("reasons") or []),
    }


def _compact_messages(messages):
    details = [str(message or "").strip() for message in messages if str(message or "").strip()]
    if not details:
        return ""

    detail = "; ".join(details[:DETAIL_MESSAGE_LIMIT])
    if len(details) > DETAIL_MESSAGE_LIMIT:
        detail = _("{0}; (+{1} more)").format(detail, len(details) - DETAIL_MESSAGE_LIMIT)
    return detail


def _format_matrix_cell(course_row):
    row_status = (course_row.get("status") or "").strip()
    if row_status in {"Approved", "Rejected", "Waitlisted"}:
        return row_status

    choice_rank = course_row.get("choice_rank")
    if choice_rank:
        return _("Choice {0}").format(choice_rank)
    if cint(course_row.get("required")) == 1:
        return _("Required")
    return _("Selected")


def _build_summary_view(requests, course_catalog):
    aggregates = {}
    course_names = {}
    required_map = {}

    for meta in course_catalog or []:
        course = meta["course"]
        course_names[course] = meta.get("course_name") or ""
        required_map[course] = 1 if cint(meta.get("required")) == 1 else 0
        aggregates[course] = _empty_summary_row(course, course_names[course], required_map[course])

    for request in requests or []:
        invalid_buckets = request.get("invalid_reason_buckets") or []
        for course_row in request.get("courses") or []:
            course = (course_row.get("course") or "").strip()
            if not course:
                continue
            course_names.setdefault(course, (course_row.get("course_name") or "").strip())
            required_map[course] = 1 if required_map.get(course) or cint(course_row.get("required")) == 1 else 0
            row = aggregates.setdefault(
                course,
                _empty_summary_row(course, course_names.get(course) or "", required_map.get(course) or 0),
            )
            row["students_requested"] += 1
            if request.get("validation_status") == "Valid":
                row["valid_requests"] += 1
            elif request.get("validation_status") == "Invalid":
                row["invalid_requests"] += 1
                for bucket in invalid_buckets:
                    row["_invalid_reason_counts"][bucket] += 1
            if request.get("request_status") == "Approved":
                row["approved_requests"] += 1
            if cint(request.get("requires_override")) == 1:
                row["requires_override"] += 1

    rows = []
    for meta in course_catalog or []:
        course = meta["course"]
        rows.append(_finalize_summary_row(aggregates[course]))

    for course, row in sorted(aggregates.items(), key=lambda item: (_course_sort_label(item[0], item[1]), item[0])):
        if any(meta["course"] == course for meta in course_catalog):
            continue
        rows.append(_finalize_summary_row(row))

    columns = [
        {"label": _("Course"), "fieldname": "course", "fieldtype": "Link", "options": "Course", "width": 160},
        {"label": _("Course Name"), "fieldname": "course_name", "fieldtype": "Data", "width": 220},
        {"label": _("Required"), "fieldname": "required", "fieldtype": "Check", "width": 90},
        {"label": _("Students Requested"), "fieldname": "students_requested", "fieldtype": "Int", "width": 130},
        {"label": _("Valid Requests"), "fieldname": "valid_requests", "fieldtype": "Int", "width": 120},
        {"label": _("Invalid Requests"), "fieldname": "invalid_requests", "fieldtype": "Int", "width": 120},
        {"label": _("Approved Requests"), "fieldname": "approved_requests", "fieldtype": "Int", "width": 130},
        {"label": _("Needs Override"), "fieldname": "requires_override", "fieldtype": "Int", "width": 120},
        {"label": _("Top Invalid Reasons"), "fieldname": "top_invalid_reasons", "fieldtype": "Data", "width": 260},
    ]
    return columns, rows


def _empty_summary_row(course, course_name, required):
    return {
        "course": course,
        "course_name": course_name or "",
        "required": 1 if cint(required) == 1 else 0,
        "students_requested": 0,
        "valid_requests": 0,
        "invalid_requests": 0,
        "approved_requests": 0,
        "requires_override": 0,
        "_invalid_reason_counts": Counter(),
    }


def _finalize_summary_row(row):
    output = dict(row)
    output["top_invalid_reasons"] = _format_top_invalid_reasons(output.pop("_invalid_reason_counts", Counter()))
    return output


def _format_top_invalid_reasons(reason_counts):
    if not reason_counts:
        return ""
    parts = []
    for bucket, count in sorted(
        reason_counts.items(),
        key=lambda item: (
            -item[1],
            INVALID_REASON_BUCKETS.index(item[0]) if item[0] in INVALID_REASON_BUCKETS else len(INVALID_REASON_BUCKETS),
        ),
    ):
        parts.append(_("{0} ({1})").format(bucket, count))
        if len(parts) == 3:
            break
    return ", ".join(parts)


def _course_sort_label(course, row):
    label = (row.get("course_name") or "").strip()
    return label or (course or "")


def _build_course_demand_chart(rows):
    ranked = sorted(rows or [], key=lambda row: (-int(row.get("students_requested") or 0), row.get("course") or ""))
    ranked = [row for row in ranked if int(row.get("students_requested") or 0) > 0][:12]
    if not ranked:
        return {}

    return {
        "data": {
            "labels": [row.get("course") for row in ranked],
            "datasets": [
                {"name": _("Students Requested"), "values": [row.get("students_requested") for row in ranked]}
            ],
        },
        "type": "bar",
    }


def _build_request_status_chart(requests):
    if not requests:
        return {}

    counts = Counter()
    for request in requests or []:
        counts[(request.get("request_status") or "").strip() or _("Unknown")] += 1

    labels = [status for status in STATUS_ORDER if counts.get(status)]
    if counts.get(_("Unknown")):
        labels.append(_("Unknown"))
    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": _("Requests"), "values": [counts.get(label, 0) for label in labels]}],
        },
        "type": "bar",
    }


def _build_report_summary(requests):
    total = len(requests or [])
    valid = sum(1 for request in requests if request.get("validation_status") == "Valid")
    invalid = sum(1 for request in requests if request.get("validation_status") == "Invalid")
    approved = sum(1 for request in requests if request.get("request_status") == "Approved")
    overrides = sum(1 for request in requests if cint(request.get("requires_override")) == 1)
    return [
        {"value": total, "label": _("Requests"), "indicator": "blue", "datatype": "Int"},
        {"value": valid, "label": _("Valid"), "indicator": "green", "datatype": "Int"},
        {"value": invalid, "label": _("Invalid"), "indicator": "red", "datatype": "Int"},
        {"value": approved, "label": _("Approved"), "indicator": "blue", "datatype": "Int"},
        {"value": overrides, "label": _("Needs Override"), "indicator": "orange", "datatype": "Int"},
    ]


def _build_window_submission_chart(rows):
    counts = {
        SUBMISSION_STATUS_SUBMITTED: 0,
        SUBMISSION_STATUS_NOT_SUBMITTED: 0,
        SUBMISSION_STATUS_MISSING_REQUEST: 0,
    }
    for row in rows or []:
        status = (row.get("submission_status") or "").strip()
        if status in counts:
            counts[status] += 1

    labels = [label for label, count in counts.items() if count]
    if not labels:
        return {}

    return {
        "data": {
            "labels": labels,
            "datasets": [{"name": _("Students"), "values": [counts[label] for label in labels]}],
        },
        "type": "bar",
    }


def _build_window_tracker_summary(rows):
    total = len(rows or [])
    submitted = sum(1 for row in rows if row.get("submission_status") == SUBMISSION_STATUS_SUBMITTED)
    not_submitted = sum(1 for row in rows if row.get("submission_status") == SUBMISSION_STATUS_NOT_SUBMITTED)
    missing_request = sum(1 for row in rows if row.get("submission_status") == SUBMISSION_STATUS_MISSING_REQUEST)
    problematic = sum(1 for row in rows if row.get("problem_status"))
    return [
        {"value": total, "label": _("Students"), "indicator": "blue", "datatype": "Int"},
        {"value": submitted, "label": _("Submitted"), "indicator": "green", "datatype": "Int"},
        {"value": not_submitted, "label": _("Not Submitted"), "indicator": "orange", "datatype": "Int"},
        {"value": missing_request, "label": _("Missing Request"), "indicator": "red", "datatype": "Int"},
        {"value": problematic, "label": _("Problematic"), "indicator": "red", "datatype": "Int"},
    ]


def _extract_invalid_reason_info(row):
    if (row.get("validation_status") or "").strip() != "Invalid":
        return {"buckets": [], "summary": "", "detail": ""}

    payload = _safe_parse_json(row.get("validation_payload"))
    if not payload:
        return {
            "buckets": ["Other"],
            "summary": "Other",
            "detail": _("Validation payload is missing or unreadable."),
        }

    buckets = []
    details = []
    seen_details = set()

    basket = (payload.get("results") or {}).get("basket") or {}
    for violation in basket.get("violations") or []:
        code = ((violation or {}).get("code") or "").strip()
        message = ((violation or {}).get("message") or "").strip()
        _append_bucket(buckets, _bucket_from_basket_issue(code, message))
        _append_detail(details, seen_details, _humanize_basket_issue(code, message))

    for message in basket.get("reasons") or []:
        message = (message or "").strip()
        _append_bucket(buckets, _bucket_from_basket_issue("", message))
        _append_detail(details, seen_details, _humanize_basket_issue("", message))

    for course_row in (payload.get("results") or {}).get("courses") or []:
        course = (course_row.get("course") or "").strip()
        for reason in course_row.get("reasons") or []:
            reason = (reason or "").strip()
            _append_bucket(buckets, _bucket_from_course_reason(reason))
            _append_detail(details, seen_details, _humanize_course_reason(course, reason))

    if not buckets:
        buckets.append("Other")
    if not details:
        details.append(_("Request needs academic review."))

    summary = ", ".join(buckets)
    detail = "; ".join(details[:DETAIL_MESSAGE_LIMIT])
    if len(details) > DETAIL_MESSAGE_LIMIT:
        detail = _("{0}; (+{1} more)").format(detail, len(details) - DETAIL_MESSAGE_LIMIT)

    return {
        "buckets": buckets,
        "summary": summary,
        "detail": detail,
    }


def _safe_parse_json(value):
    if not value:
        return None
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return None


def _append_bucket(buckets, bucket):
    if bucket and bucket not in buckets:
        buckets.append(bucket)


def _append_detail(details, seen_details, detail):
    normalized = (detail or "").strip()
    if not normalized or normalized in seen_details:
        return
    seen_details.add(normalized)
    details.append(normalized)


def _bucket_from_basket_issue(code, message):
    if code == "missing_required" or message == "Missing required courses in basket.":
        return "Basket Missing Required"
    if code == "ambiguous_basket_group" or "assigned to a basket group" in message:
        return "Basket Group Not Selected"
    if code == "require_group_coverage" or message.startswith("Basket must include at least one course from group"):
        return "Basket Group Coverage"
    if code in {"unsupported_rule", "misconfigured_rule", "unknown_rule_type"}:
        return "Rule Misconfigured / Unsupported"
    return None


def _bucket_from_course_reason(reason):
    if not reason:
        return None
    if reason == "Capacity full for this course.":
        return "Capacity Full"
    if reason == "Course is not part of the Program Offering.":
        return "Course Not In Offering"
    if reason in {"Course already completed and not repeatable.", "Maximum attempts exceeded."}:
        return "Repeat / Max Attempts"
    if reason == "Rule not supported by current schema.":
        return "Rule Misconfigured / Unsupported"
    if (
        reason == "Prerequisite requirements not met."
        or reason.startswith("Required course ")
        or reason.startswith("No numeric score evidence for ")
        or (reason.startswith("Required ") and " score " in reason and "; got " in reason)
    ):
        return "Prerequisite"
    return "Other"


def _humanize_basket_issue(code, message):
    if code == "missing_required" or message == "Missing required courses in basket.":
        return _("A required course is missing from the request.")
    if code == "ambiguous_basket_group" or "assigned to a basket group" in message:
        return _("A selected course still needs a basket-group choice before the request can advance.")
    if code == "require_group_coverage" or message.startswith("Basket must include at least one course from group"):
        return message or _("A required basket-group choice is still missing.")
    return message or ""


def _humanize_course_reason(course, reason):
    if not reason:
        return ""
    course = course or _("Selected course")
    if reason == "Capacity full for this course.":
        return _("No places are currently available in {0}.").format(course)
    if reason == "Course is not part of the Program Offering.":
        return _("{0} is no longer part of this program offering.").format(course)
    if (
        reason
        in {
            "Prerequisite requirements not met.",
            "Rule not supported by current schema.",
        }
        or reason.startswith("Required course ")
        or reason.startswith("No numeric score evidence for ")
        or (reason.startswith("Required ") and " score " in reason and "; got " in reason)
    ):
        return _("{0} needs prerequisite review before the request can advance.").format(course)
    if reason == "Course already completed and not repeatable.":
        return _("{0} has already been completed and cannot be selected again.").format(course)
    if reason == "Maximum attempts exceeded.":
        return _("{0} has already reached the maximum number of attempts.").format(course)
    return _("{0}: {1}").format(course, reason)
