# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/term_reporting.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.utilities.employee_utils import get_user_visible_schools

TERM_REPORTING_REVIEW_ROLES = {
    "Academic Admin",
    "Academic Assistant",
    "Academic Staff",
    "Administrator",
    "Curriculum Coordinator",
    "Instructor",
    "System Manager",
}

UNRESTRICTED_REVIEW_ROLES = {"Administrator", "System Manager"}

REPORTING_CYCLE_FIELDS = [
    "name",
    "school",
    "academic_year",
    "term",
    "program",
    "assessment_scheme",
    "assessment_calculation_method",
    "name_label",
    "task_cutoff_date",
    "status",
]

COURSE_TERM_RESULT_FIELDS = [
    "name",
    "student",
    "program_enrollment",
    "course",
    "program",
    "academic_year",
    "term",
    "assessment_scheme",
    "assessment_calculation_method",
    "grade_scale",
    "numeric_score",
    "grade_value",
    "override_grade_value",
    "task_counted",
    "total_weight",
    "internal_note",
]

COURSE_TERM_RESULT_COMPONENT_FIELDS = [
    "parent",
    "component_type",
    "component_key",
    "label",
    "assessment_category",
    "assessment_criteria",
    "weight",
    "raw_score",
    "weighted_score",
    "grade_value",
    "evidence_count",
    "included_outcome_count",
    "excluded_outcome_count",
    "calculation_note",
]


def _row_value(row, fieldname):
    if hasattr(row, "get"):
        return row.get(fieldname)
    return getattr(row, fieldname, None)


def _copy_row(row, fields):
    return {fieldname: _row_value(row, fieldname) for fieldname in fields}


def _clean_link(value) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_int(value, default: int, *, minimum: int = 0, maximum: int | None = None) -> int:
    try:
        normalized = int(value if value is not None else default)
    except Exception:
        normalized = default
    normalized = max(normalized, minimum)
    if maximum is not None:
        normalized = min(normalized, maximum)
    return normalized


def _current_user() -> str:
    user = _clean_link(getattr(frappe.session, "user", None))
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access Term Reporting Review."), frappe.PermissionError)
    return user


def _ensure_review_access() -> tuple[str, set[str], list[str] | None]:
    user = _current_user()
    roles = set(frappe.get_roles(user) or [])
    if not roles & TERM_REPORTING_REVIEW_ROLES:
        frappe.throw(_("You do not have permission to access Term Reporting Review."), frappe.PermissionError)

    school_scope = get_user_visible_schools(user) or []
    if school_scope:
        return user, roles, school_scope

    if roles & UNRESTRICTED_REVIEW_ROLES:
        return user, roles, None

    return user, roles, []


def _cycle_filters_for_scope(school_scope: list[str] | None) -> dict:
    if school_scope is None:
        return {}
    if not school_scope:
        return {"name": ["in", []]}
    return {"school": ["in", school_scope]}


def _load_reporting_cycles(school_scope: list[str] | None, *, limit: int = 50) -> list[dict]:
    if school_scope == []:
        return []

    rows = frappe.get_all(
        "Reporting Cycle",
        filters=_cycle_filters_for_scope(school_scope),
        fields=REPORTING_CYCLE_FIELDS,
        order_by="modified desc",
        limit=limit,
    )
    return [_copy_row(row, REPORTING_CYCLE_FIELDS) for row in rows or []]


def _load_reporting_cycle(reporting_cycle: str, school_scope: list[str] | None) -> dict | None:
    row = frappe.db.get_value(
        "Reporting Cycle",
        reporting_cycle,
        REPORTING_CYCLE_FIELDS,
        as_dict=True,
    )
    if not row:
        return None

    cycle = _copy_row(row, REPORTING_CYCLE_FIELDS)
    if school_scope is not None and cycle.get("school") not in set(school_scope or []):
        frappe.throw(_("You do not have access to this Reporting Cycle."), frappe.PermissionError)
    return cycle


def _course_term_result_filters(reporting_cycle, course=None, student=None, program=None) -> dict:
    filters = {"reporting_cycle": reporting_cycle}
    if course:
        filters["course"] = course
    if student:
        filters["student"] = student
    if program:
        filters["program"] = program
    return filters


def _load_course_term_results(filters: dict, *, limit: int, start: int) -> list[dict]:
    rows = frappe.get_all(
        "Course Term Result",
        filters=filters,
        fields=COURSE_TERM_RESULT_FIELDS,
        limit_start=start,
        limit=limit,
        order_by="student asc, course asc",
    )

    normalized_rows = [_copy_row(row, COURSE_TERM_RESULT_FIELDS) for row in rows or []]
    result_names = [row["name"] for row in normalized_rows if row.get("name")]
    components_by_parent = {name: [] for name in result_names}

    if result_names:
        component_rows = frappe.get_all(
            "Course Term Result Component",
            filters={
                "parent": ("in", result_names),
                "parenttype": "Course Term Result",
                "parentfield": "components",
            },
            fields=COURSE_TERM_RESULT_COMPONENT_FIELDS,
            order_by="parent asc, idx asc",
            limit=0,
        )
        for component_row in component_rows or []:
            parent = _row_value(component_row, "parent")
            if parent not in components_by_parent:
                continue
            component = _copy_row(component_row, COURSE_TERM_RESULT_COMPONENT_FIELDS)
            component.pop("parent", None)
            components_by_parent[parent].append(component)

    for row in normalized_rows:
        row["components"] = components_by_parent.get(row["name"], [])

    return normalized_rows


def _cycle_summary(cycle: dict, *, result_count: int) -> dict:
    return {
        "reporting_cycle": cycle.get("name"),
        "school": cycle.get("school"),
        "academic_year": cycle.get("academic_year"),
        "term": cycle.get("term"),
        "program": cycle.get("program"),
        "status": cycle.get("status"),
        "assessment_scheme": cycle.get("assessment_scheme"),
        "assessment_calculation_method": cycle.get("assessment_calculation_method"),
        "name_label": cycle.get("name_label"),
        "task_cutoff_date": cycle.get("task_cutoff_date"),
        "course_term_results": result_count,
    }


@frappe.whitelist()
def get_cycle_summary(reporting_cycle):
    if not reporting_cycle:
        frappe.throw(_("Reporting Cycle is required."))

    cycle = frappe.db.get_value(
        "Reporting Cycle",
        reporting_cycle,
        ["name", "school", "academic_year", "term", "program", "status"],
        as_dict=True,
    )
    if not cycle:
        frappe.throw(_("Reporting Cycle not found."))

    result_count = frappe.db.count("Course Term Result", {"reporting_cycle": reporting_cycle})

    return {
        "reporting_cycle": cycle.name,
        "school": cycle.school,
        "academic_year": cycle.academic_year,
        "term": cycle.term,
        "program": cycle.program,
        "status": cycle.status,
        "course_term_results": result_count,
    }


@frappe.whitelist()
def get_course_term_results(reporting_cycle, course=None, student=None, program=None, limit=100, start=0):
    if not reporting_cycle:
        frappe.throw(_("Reporting Cycle is required."))

    limit = _normalize_int(limit, 100, minimum=1, maximum=500)
    start = _normalize_int(start, 0, minimum=0)
    filters = _course_term_result_filters(
        reporting_cycle,
        course=_clean_link(course),
        student=_clean_link(student),
        program=_clean_link(program),
    )
    rows = _load_course_term_results(filters, limit=limit, start=start)
    return {"rows": rows, "count": len(rows)}


@frappe.whitelist()
def get_review_surface(reporting_cycle=None, course=None, student=None, program=None, limit=50, start=0):
    _user, _roles, school_scope = _ensure_review_access()
    limit = _normalize_int(limit, 50, minimum=1, maximum=100)
    start = _normalize_int(start, 0, minimum=0)

    requested_cycle = _clean_link(reporting_cycle)
    cycles = _load_reporting_cycles(school_scope)

    if requested_cycle:
        selected_cycle = _load_reporting_cycle(requested_cycle, school_scope)
        if not selected_cycle:
            frappe.throw(_("Reporting Cycle not found."))
    elif cycles:
        selected_cycle = _load_reporting_cycle(cycles[0]["name"], school_scope) or cycles[0]
    else:
        selected_cycle = None

    if selected_cycle and selected_cycle["name"] not in {cycle["name"] for cycle in cycles}:
        cycles = [selected_cycle, *cycles]

    if not selected_cycle:
        return {
            "cycles": cycles,
            "selected_reporting_cycle": None,
            "cycle": None,
            "filters": {
                "reporting_cycle": None,
                "course": _clean_link(course),
                "student": _clean_link(student),
                "program": _clean_link(program),
            },
            "results": {
                "rows": [],
                "total_count": 0,
                "page_count": 0,
                "start": start,
                "limit": limit,
            },
        }

    result_filters = _course_term_result_filters(
        selected_cycle["name"],
        course=_clean_link(course),
        student=_clean_link(student),
        program=_clean_link(program),
    )
    total_count = frappe.db.count("Course Term Result", result_filters)
    rows = _load_course_term_results(result_filters, limit=limit, start=start)

    return {
        "cycles": cycles,
        "selected_reporting_cycle": selected_cycle["name"],
        "cycle": _cycle_summary(selected_cycle, result_count=total_count),
        "filters": {
            "reporting_cycle": selected_cycle["name"],
            "course": _clean_link(course),
            "student": _clean_link(student),
            "program": _clean_link(program),
        },
        "results": {
            "rows": rows,
            "total_count": total_count,
            "page_count": len(rows),
            "start": start,
            "limit": limit,
        },
    }
