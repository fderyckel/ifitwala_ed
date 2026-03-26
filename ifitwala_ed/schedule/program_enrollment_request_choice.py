# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.schedule.basket_group_utils import get_offering_course_semantics
from ifitwala_ed.schedule.enrollment_engine import evaluate_basket_selection


def _normalize_choice_rank(value) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        rank = int(text)
    except (TypeError, ValueError):
        frappe.throw(_("Choice Rank must be a positive whole number."))

    if rank == 0:
        return None
    if rank < 0:
        frappe.throw(_("Choice Rank must be a positive whole number."))
    return rank


def _normalize_rows(rows) -> list[dict]:
    normalized = []
    seen = set()

    for row in rows or []:
        course = (getattr(row, "course", None) or (row or {}).get("course") or "").strip()
        if not course or course in seen:
            continue
        seen.add(course)
        normalized.append(
            {
                "course": course,
                "required": 1 if int(getattr(row, "required", None) or (row or {}).get("required") or 0) == 1 else 0,
                "applied_basket_group": (
                    getattr(row, "applied_basket_group", None) or (row or {}).get("applied_basket_group") or ""
                ).strip(),
                "choice_rank": _normalize_choice_rank(
                    getattr(row, "choice_rank", None) if hasattr(row, "choice_rank") else (row or {}).get("choice_rank")
                ),
            }
        )

    return normalized


def _required_offering_basket_groups(program_offering: str) -> list[str]:
    if not program_offering:
        return []

    rows = frappe.get_all(
        "Program Offering Enrollment Rule",
        filters={
            "parent": program_offering,
            "parenttype": "Program Offering",
            "rule_type": "REQUIRE_GROUP_COVERAGE",
        },
        fields=["basket_group"],
        order_by="idx asc",
    )

    output = []
    seen = set()
    for row in rows or []:
        basket_group = (row.get("basket_group") or "").strip()
        if not basket_group or basket_group in seen:
            continue
        seen.add(basket_group)
        output.append(basket_group)
    return output


def get_effective_program_enrollment_request_rows(request) -> list[dict]:
    explicit_rows = _normalize_rows(request.get("courses") or [])
    offering_semantics = get_offering_course_semantics((request.program_offering or "").strip())
    effective_rows = []
    seen = set()

    for row in explicit_rows:
        course = row.get("course")
        if not course or course in seen:
            continue
        if offering_semantics and course not in offering_semantics:
            continue
        seen.add(course)

        semantics = offering_semantics.get(course) or {}
        effective_rows.append(
            {
                "course": course,
                "required": 1 if semantics.get("required") else 0,
                "applied_basket_group": (row.get("applied_basket_group") or "").strip(),
                "choice_rank": _normalize_choice_rank(row.get("choice_rank")),
            }
        )

    for course, semantics in offering_semantics.items():
        if not semantics.get("required") or course in seen:
            continue
        effective_rows.append(
            {
                "course": course,
                "required": 1,
                "applied_basket_group": "",
                "choice_rank": None,
            }
        )

    return effective_rows


def get_program_enrollment_request_choice_state(request, *, can_edit: bool) -> dict:
    offering_name = (request.program_offering or "").strip()
    offering_semantics = get_offering_course_semantics(offering_name) if offering_name else {}
    explicit_rows = _normalize_rows(request.get("courses") or [])
    explicit_by_course = {row["course"]: row for row in explicit_rows}
    effective_rows = get_effective_program_enrollment_request_rows(request)
    effective_by_course = {row["course"]: row for row in effective_rows}
    required_basket_groups = _required_offering_basket_groups(offering_name)
    basket_result = (
        evaluate_basket_selection(program_offering=offering_name, requested_courses=effective_rows)
        if offering_name
        else {
            "status": None,
            "override_required": False,
            "reasons": [],
            "violations": [],
            "missing_required_courses": [],
            "ambiguous_courses": [],
            "group_summary": {},
        }
    )

    courses = []
    required_count = 0
    optional_count = 0
    selected_optional_count = 0

    for course, semantics in offering_semantics.items():
        effective_row = effective_by_course.get(course) or {}
        basket_groups = list(semantics.get("basket_groups") or [])
        required = bool(semantics.get("required"))
        is_selected = required or course in explicit_by_course
        applied_basket_group = (effective_row.get("applied_basket_group") or "").strip()
        choice_rank = effective_row.get("choice_rank")

        if required:
            required_count += 1
        else:
            optional_count += 1
            if course in explicit_by_course:
                selected_optional_count += 1

        courses.append(
            {
                "course": course,
                "course_name": (semantics.get("course_name") or "").strip() or course,
                "required": required,
                "basket_groups": basket_groups,
                "applied_basket_group": applied_basket_group or None,
                "choice_rank": choice_rank,
                "is_selected": bool(is_selected),
                "requires_basket_group_selection": bool(
                    is_selected and len(basket_groups) > 1 and not applied_basket_group
                ),
                "is_explicit_choice": bool(course in explicit_by_course),
                "has_choice_rank": choice_rank is not None,
            }
        )

    basket_status = (basket_result.get("status") or "").strip() or None
    ready_for_submit = basket_status in {"ok", "not_configured"}
    request_status = (request.status or "").strip() or "Draft"

    return {
        "request": {
            "name": request.name,
            "status": request_status,
            "academic_year": (request.academic_year or "").strip(),
            "program": (request.program or "").strip(),
            "program_offering": offering_name,
            "validation_status": (request.validation_status or "").strip() or "Not Validated",
            "submitted_on": request.submitted_on,
            "submitted_by": (request.submitted_by or "").strip() or None,
            "can_edit_choices": bool(can_edit),
            "can_submit_choices": bool(can_edit),
        },
        "summary": {
            "has_request": True,
            "has_courses": bool(courses),
            "has_selectable_courses": any(not bool(row.get("required")) for row in courses),
            "can_edit_choices": bool(can_edit),
            "ready_for_submit": ready_for_submit,
            "required_course_count": required_count,
            "optional_course_count": optional_count,
            "selected_optional_count": selected_optional_count,
        },
        "validation": {
            "status": basket_status,
            "ready_for_submit": ready_for_submit,
            "reasons": list(basket_result.get("reasons") or []),
            "violations": list(basket_result.get("violations") or []),
            "missing_required_courses": list(basket_result.get("missing_required_courses") or []),
            "ambiguous_courses": list(basket_result.get("ambiguous_courses") or []),
            "group_summary": dict(basket_result.get("group_summary") or {}),
        },
        "required_basket_groups": required_basket_groups,
        "courses": courses,
    }


def store_program_enrollment_request_choices(request, *, courses: list[dict] | None = None) -> None:
    if not request.program_offering:
        frappe.throw(_("Program Offering is required before course choices can be updated."))

    submitted_rows = _normalize_rows(courses or [])
    submitted_by_course = {row["course"]: row for row in submitted_rows}
    offering_semantics = get_offering_course_semantics(request.program_offering)
    allowed_courses = set(offering_semantics.keys())
    unknown_courses = sorted(course for course in submitted_by_course if course not in allowed_courses)
    if unknown_courses:
        frappe.throw(
            _("One or more selected courses are not part of this Program Offering: {0}.").format(
                ", ".join(unknown_courses)
            )
        )

    current_rows = _normalize_rows(request.get("courses") or [])
    current_by_course = {row["course"]: row for row in current_rows}
    rows_to_store = []

    for course, semantics in offering_semantics.items():
        current = current_by_course.get(course) or {}
        submitted = submitted_by_course.get(course) or {}
        if semantics.get("required"):
            rows_to_store.append(
                {
                    "course": course,
                    "required": 1,
                    "applied_basket_group": (
                        submitted.get("applied_basket_group") or current.get("applied_basket_group") or ""
                    ),
                    "choice_rank": submitted.get("choice_rank")
                    if "choice_rank" in submitted
                    else current.get("choice_rank"),
                }
            )
            continue

        if not submitted:
            continue

        rows_to_store.append(
            {
                "course": course,
                "required": 0,
                "applied_basket_group": submitted.get("applied_basket_group") or "",
                "choice_rank": submitted.get("choice_rank"),
            }
        )

    request.set("courses", rows_to_store)
    request.validation_status = "Not Validated"
    request.validation_payload = None
    request.validated_on = None
    request.validated_by = None
    request.requires_override = 0
