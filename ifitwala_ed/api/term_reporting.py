# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


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
		fields=[
			"name",
			"student",
			"program_enrollment",
			"course",
			"program",
			"academic_year",
			"term",
			"numeric_score",
			"grade_value",
			"override_grade_value",
			"task_counted",
			"total_weight",
			"internal_note",
		],
		limit_start=start,
		limit_page_length=limit,
		order_by="student asc, course asc",
	)

	return {"rows": rows, "count": len(rows)}
