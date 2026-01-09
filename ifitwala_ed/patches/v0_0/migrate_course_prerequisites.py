# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _


DEFAULT_MIN_GRADE = "0"


def execute():
	if not frappe.db.table_exists("Course Prerequisite"):
		return

	course_prereqs = frappe.db.get_all(
		"Course Prerequisite",
		filters={"parenttype": "Course"},
		fields=[
			"parent",
			"required_course",
			"min_grade_default",
			"concurrency_ok_default",
			"notes",
		],
	)
	if not course_prereqs:
		return

	program_course_rows = frappe.db.get_all(
		"Program Course",
		fields=["parent", "course"],
	)
	programs_by_course = defaultdict(set)
	program_names = set()
	for row in program_course_rows:
		course = row.get("course")
		program = row.get("parent")
		if course and program:
			programs_by_course[course].add(program)
			program_names.add(program)

	existing = frappe.db.get_all(
		"Program Course Prerequisite",
		fields=["parent", "apply_to_course", "required_course"],
	)
	existing_keys = {
		(row.get("parent"), row.get("apply_to_course"), row.get("required_course"))
		for row in existing
	}

	required_courses = {row.get("required_course") for row in course_prereqs if row.get("required_course")}
	course_scales = {}
	if required_courses:
		course_scales = {
			row.get("name"): row.get("grade_scale")
			for row in frappe.db.get_all(
				"Course",
				filters={"name": ["in", list(required_courses)]},
				fields=["name", "grade_scale"],
			)
		}

	program_scales = {}
	if program_names:
		program_scales = {
			row.get("name"): row.get("grade_scale")
			for row in frappe.db.get_all(
				"Program",
				filters={"name": ["in", list(program_names)]},
				fields=["name", "grade_scale"],
			)
		}

	rows_by_program = defaultdict(list)
	for row in course_prereqs:
		apply_to_course = row.get("parent")
		required_course = row.get("required_course")
		if not apply_to_course or not required_course:
			continue

		min_grade = (row.get("min_grade_default") or "").strip() or DEFAULT_MIN_GRADE

		for program in programs_by_course.get(apply_to_course, set()):
			key = (program, apply_to_course, required_course)
			if key in existing_keys:
				continue

			grade_scale = course_scales.get(required_course) or program_scales.get(program)
			if not grade_scale:
				frappe.throw(
					_(
						"Cannot migrate prerequisites for course {0} in program {1}: no grade scale found. "
						"Set Course.grade_scale or Program.grade_scale."
					).format(apply_to_course, program)
				)

			rows_by_program[program].append({
				"apply_to_course": apply_to_course,
				"required_course": required_course,
				"min_grade": min_grade,
				"concurrency_ok": int(row.get("concurrency_ok_default") or 0),
				"notes": row.get("notes"),
				"prereq_group": 1,
			})

	for program, rows in rows_by_program.items():
		if not rows:
			continue
		doc = frappe.get_doc("Program", program)
		for row in rows:
			doc.append("prerequisites", row)
		doc.save(ignore_permissions=True)
