# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def resolve_grade_scale(program_offering, course):
    if not program_offering:
        frappe.throw(_("Program Offering is required."))
    if not course:
        frappe.throw(_("Course is required."))

    trace = []

    offering_course_scale = frappe.db.get_value(
        "Program Offering Course",
        {
            "parent": program_offering,
            "parenttype": "Program Offering",
            "course": course,
        },
        "grade_scale",
    )
    trace.append({"layer": "Program Offering Course", "value": offering_course_scale})

    offering = (
        frappe.db.get_value(
            "Program Offering",
            program_offering,
            ["grade_scale", "program"],
            as_dict=True,
        )
        or {}
    )
    trace.append({"layer": "Program Offering", "value": offering.get("grade_scale")})

    course_scales = (
        frappe.db.get_value(
            "Course",
            course,
            ["grade_scale", "default_grade_scale"],
            as_dict=True,
        )
        or {}
    )
    trace.append({"layer": "Course.grade_scale", "value": course_scales.get("grade_scale")})
    trace.append({"layer": "Course.default_grade_scale", "value": course_scales.get("default_grade_scale")})

    program_scale = None
    program = offering.get("program")
    if program:
        program_scale = frappe.db.get_value("Program", program, "grade_scale")
    trace.append({"layer": "Program.grade_scale", "value": program_scale})

    for entry in trace:
        if entry.get("value"):
            return {"grade_scale": entry["value"], "trace": trace}

    return {"grade_scale": None, "trace": trace}
