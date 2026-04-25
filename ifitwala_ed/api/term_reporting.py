# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/term_reporting.py

import frappe
from frappe import _

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

    try:
        limit = int(limit or 100)
    except Exception:
        limit = 100
    try:
        start = int(start or 0)
    except Exception:
        start = 0

    filters = {"reporting_cycle": reporting_cycle}
    if course:
        filters["course"] = course
    if student:
        filters["student"] = student
    if program:
        filters["program"] = program

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

    return {"rows": normalized_rows, "count": len(normalized_rows)}
