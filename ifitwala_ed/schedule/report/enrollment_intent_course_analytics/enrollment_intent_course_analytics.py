# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.schedule.enrollment_intent import (
    INTENT_DOES_NOT_INTEND,
    INTENT_UNDECIDED,
    is_enrollment_intent_affirmative,
    is_enrollment_intent_missing,
)
from ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview import (
    VIEW_MODE_SUMMARY,
    get_filtered_requests,
)


def execute(filters=None):
    filters = frappe._dict(filters or {})
    filters["view_mode"] = VIEW_MODE_SUMMARY
    filters["request_kind"] = "Academic"
    filters["latest_request_only"] = 1 if cint(filters.get("latest_request_only", 1)) == 1 else 0

    _normalized_filters, requests = get_filtered_requests(filters, require_matrix_offering=False)
    materialized_requests = _get_materialized_request_names([row.get("name") for row in requests or []])
    rows = _build_course_rows(requests, materialized_requests)
    columns = _columns()
    chart = _chart(rows)
    summary = _summary(requests, materialized_requests)
    return columns, rows, None, chart, summary


def _columns():
    return [
        {
            "label": _("Program Offering"),
            "fieldname": "program_offering",
            "fieldtype": "Link",
            "options": "Program Offering",
            "width": 170,
        },
        {"label": _("Course"), "fieldname": "course", "fieldtype": "Link", "options": "Course", "width": 150},
        {"label": _("Course Name"), "fieldname": "course_name", "fieldtype": "Data", "width": 220},
        {"label": _("Required"), "fieldname": "required", "fieldtype": "Check", "width": 90},
        {"label": _("Intent Students"), "fieldname": "intent_students", "fieldtype": "Int", "width": 120},
        {"label": _("Submitted"), "fieldname": "submitted", "fieldtype": "Int", "width": 100},
        {"label": _("Valid"), "fieldname": "valid", "fieldtype": "Int", "width": 90},
        {"label": _("Approved"), "fieldname": "approved", "fieldtype": "Int", "width": 100},
        {"label": _("Materialized"), "fieldname": "materialized", "fieldtype": "Int", "width": 110},
        {"label": _("Needs Override"), "fieldname": "needs_override", "fieldtype": "Int", "width": 120},
        {"label": _("Basket Groups"), "fieldname": "basket_groups", "fieldtype": "Data", "width": 220},
    ]


def _build_course_rows(requests, materialized_requests):
    aggregates = {}
    student_sets = {}
    basket_groups = {}

    for request in requests or []:
        if not is_enrollment_intent_affirmative(
            request.get("enrollment_intent"),
            collect_enrollment_intent=request.get("collect_enrollment_intent"),
        ):
            continue

        request_name = (request.get("name") or "").strip()
        request_status = (request.get("request_status") or "").strip()
        validation_status = (request.get("validation_status") or "").strip()
        program_offering = (request.get("program_offering") or "").strip()
        student = (request.get("student") or "").strip()

        for course_row in request.get("courses") or []:
            course = (course_row.get("course") or "").strip()
            if not course:
                continue
            key = (program_offering, course)
            row = aggregates.setdefault(
                key,
                {
                    "program_offering": program_offering,
                    "course": course,
                    "course_name": (course_row.get("course_name") or "").strip(),
                    "required": 1 if cint(course_row.get("required")) == 1 else 0,
                    "intent_students": 0,
                    "submitted": 0,
                    "valid": 0,
                    "approved": 0,
                    "materialized": 0,
                    "needs_override": 0,
                    "basket_groups": "",
                },
            )
            row["required"] = 1 if row.get("required") or cint(course_row.get("required")) == 1 else 0
            if not row.get("course_name"):
                row["course_name"] = (course_row.get("course_name") or "").strip()

            student_sets.setdefault(key, set()).add(student or request_name)
            if request_status in {"Submitted", "Under Review", "Approved"}:
                row["submitted"] += 1
            if validation_status == "Valid":
                row["valid"] += 1
            if request_status == "Approved":
                row["approved"] += 1
            if request_name in materialized_requests:
                row["materialized"] += 1
            if cint(request.get("requires_override")) == 1:
                row["needs_override"] += 1

            applied_group = (course_row.get("applied_basket_group") or "").strip()
            if applied_group:
                basket_groups.setdefault(key, set()).add(applied_group)

    rows = []
    for key, row in aggregates.items():
        output = dict(row)
        output["intent_students"] = len(student_sets.get(key) or set())
        output["basket_groups"] = ", ".join(sorted(basket_groups.get(key) or []))
        rows.append(output)

    return sorted(
        rows,
        key=lambda row: (
            row.get("program_offering") or "",
            -(row.get("intent_students") or 0),
            row.get("course_name") or row.get("course") or "",
        ),
    )


def _get_materialized_request_names(request_names):
    names = [(name or "").strip() for name in (request_names or []) if (name or "").strip()]
    if not names:
        return set()
    return set(
        frappe.get_all(
            "Program Enrollment",
            filters={"program_enrollment_request": ["in", names]},
            pluck="program_enrollment_request",
        )
    )


def _summary(requests, materialized_requests):
    total = len(requests or [])
    counters = Counter()
    for request in requests or []:
        intent = request.get("enrollment_intent")
        collect_intent = request.get("collect_enrollment_intent")
        if is_enrollment_intent_affirmative(intent, collect_enrollment_intent=collect_intent):
            counters["intends"] += 1
        elif intent == INTENT_DOES_NOT_INTEND:
            counters["not_returning"] += 1
        elif intent == INTENT_UNDECIDED:
            counters["undecided"] += 1
        elif is_enrollment_intent_missing(intent, collect_enrollment_intent=collect_intent):
            counters["no_response"] += 1

    return [
        {"value": total, "label": _("Requests"), "indicator": "blue", "datatype": "Int"},
        {"value": counters["intends"], "label": _("Intends"), "indicator": "green", "datatype": "Int"},
        {"value": counters["not_returning"], "label": _("Not Returning"), "indicator": "red", "datatype": "Int"},
        {"value": counters["undecided"], "label": _("Undecided"), "indicator": "orange", "datatype": "Int"},
        {"value": counters["no_response"], "label": _("No Response"), "indicator": "orange", "datatype": "Int"},
        {"value": len(materialized_requests), "label": _("Materialized"), "indicator": "blue", "datatype": "Int"},
    ]


def _chart(rows):
    ranked = [row for row in sorted(rows or [], key=lambda item: -(item.get("intent_students") or 0)) if row]
    ranked = [row for row in ranked if int(row.get("intent_students") or 0) > 0][:12]
    if not ranked:
        return {}

    return {
        "data": {
            "labels": [row.get("course_name") or row.get("course") for row in ranked],
            "datasets": [{"name": _("Intent Students"), "values": [row.get("intent_students") for row in ranked]}],
        },
        "type": "bar",
    }
