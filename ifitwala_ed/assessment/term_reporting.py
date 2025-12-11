# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/term_reporting.py

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Iterable

import frappe
from frappe.utils import getdate, now_datetime


@dataclass
class TaskMeta:
	name: str
	course: str
	program: Optional[str]
	school: Optional[str]
	academic_year: Optional[str]
	grade_scale: Optional[str]
	due_date: Optional[str]


@dataclass
class Bucket:
	program_enrollment: str
	program_enrollment_course: str
	student: str
	course: str
	school: Optional[str]
	academic_year: Optional[str]
	program: Optional[str]
	grade_scale: Optional[str]
	pct_values: List[float]


def _load_reporting_cycle(reporting_cycle: str):
	rc = frappe.get_doc("Reporting Cycle", reporting_cycle)
	if not (rc.school and rc.academic_year and rc.term):
		frappe.throw("Reporting Cycle must have School, Academic Year and Term set before calculation.")
	return rc


def _get_term_window(term: str) -> Tuple[Optional[str], Optional[str]]:
	term_doc = frappe.get_doc("Term", term)
	return term_doc.term_start_date, term_doc.term_end_date


def _load_program_enrollments(rc):
	"""Return pe_by_name for the given Reporting Cycle scope."""
	filters = {
		"academic_year": rc.academic_year,
		"school": rc.school,
	}
	if getattr(rc, "program", None):
		filters["program"] = rc.program

	rows = frappe.get_all(
		"Program Enrollment",
		filters=filters,
		fields=["name", "student", "program", "academic_year", "school"],
	)
	pe_by_name = {r.name: r for r in rows}
	return pe_by_name


def _load_program_enrollment_courses(pe_by_name: Dict[str, dict]):
	if not pe_by_name:
		return {}, {}

	pe_names = list(pe_by_name.keys())
	rows = frappe.get_all(
		"Program Enrollment Course",
		filters={"parent": ("in", pe_names)},
		fields=["name", "parent", "course"],
	)

	# Map (student, course) -> PEC name, and PEC -> PE meta
	pec_by_student_course: Dict[Tuple[str, str], str] = {}
	pec_info: Dict[str, dict] = {}

	for r in rows:
		pe = pe_by_name.get(r.parent)
		if not pe:
			continue
		key = (pe.student, r.course)
		# If there are duplicates, keep the first – data model should avoid this.
		pec_by_student_course.setdefault(key, r.name)
		pec_info[r.name] = {
			"program_enrollment": r.parent,
			"student": pe.student,
			"course": r.course,
			"program": pe.program,
			"academic_year": pe.academic_year,
			"school": pe.school,
		}

	return pec_by_student_course, pec_info


def _load_tasks_for_cycle(rc, term_start: Optional[str], term_end: Optional[str]) -> Dict[str, TaskMeta]:
	filters = {
		"school": rc.school,
		"academic_year": rc.academic_year,
		"is_graded": 1,
	}
	if getattr(rc, "program", None):
		filters["program"] = rc.program

	if term_start and term_end:
		cutoff = rc.task_cutoff_date or term_end
		end_date = min(getdate(term_end), getdate(cutoff))
		filters["due_date"] = ["between", [term_start, end_date]]
	elif term_start:
		filters["due_date"] = [">=", term_start]
	elif term_end:
		cutoff = rc.task_cutoff_date or term_end
		end_date = min(getdate(term_end), getdate(cutoff))
		filters["due_date"] = ["<=", end_date]

	rows = frappe.get_all(
		"Task",
		filters=filters,
		fields=["name", "course", "program", "school", "academic_year", "grade_scale", "due_date"],
	)

	out: Dict[str, TaskMeta] = {}
	for r in rows:
		out[r.name] = TaskMeta(
			name=r.name,
			course=r.course,
			program=r.program,
			school=r.school,
			academic_year=r.academic_year,
			grade_scale=r.grade_scale,
			due_date=r.due_date,
		)
	return out


def _load_task_students(task_names: Iterable[str]):
	if not task_names:
		return []

	return frappe.get_all(
		"Task Student",
		filters={"parent": ("in", list(task_names)), "parenttype": "Task"},
		fields=["parent", "student", "mark_awarded", "out_of", "pct"],
	)


def _compute_pct(row) -> Optional[float]:
	"""Return a percentage for a Task Student row, or None if not computable."""
	if row.pct is not None:
		try:
			return float(row.pct)
		except Exception:
			pass

	if row.mark_awarded is None or row.out_of in (None, 0):
		return None

	try:
		ma = float(row.mark_awarded)
		out_of = float(row.out_of)
	except Exception:
		return None

	if out_of <= 0:
		return None

	return (ma / out_of) * 100.0


def _compute_grade_value(pct: Optional[float], grade_scale: Optional[str]) -> Optional[str]:
	"""Placeholder: map numeric percentage to grade value based on Grade Scale.

	Wire your real Grade Scale mapping here later.
	"""
	if pct is None or not grade_scale:
		return None
	# TODO: implement mapping based on Grade Scale configuration
	return None


@frappe.whitelist()
def recalculate_course_term_results(reporting_cycle: str):
	"""Rebuild Course Term Result rows for a Reporting Cycle from Task / Task Student.

	Idempotent: existing rows for this cycle are updated, new ones are created.
	"""
	rc = _load_reporting_cycle(reporting_cycle)
	term_start, term_end = _get_term_window(rc.term)

	pe_by_name = _load_program_enrollments(rc)
	pec_by_student_course, pec_info = _load_program_enrollment_courses(pe_by_name)

	tasks = _load_tasks_for_cycle(rc, term_start, term_end)
	if not tasks:
		return {"updated": 0, "created": 0, "buckets": 0}

	ts_rows = _load_task_students(tasks.keys())
	if not ts_rows:
		return {"updated": 0, "created": 0, "buckets": 0}

	# Aggregate percentages per Program Enrollment Course
	buckets: Dict[str, Bucket] = {}

	for row in ts_rows:
		tmeta = tasks.get(row.parent)
		if not tmeta or not tmeta.course:
			continue

		key = (row.student, tmeta.course)
		pec_name = pec_by_student_course.get(key)
		if not pec_name:
			# No Program Enrollment Course row – skip for now.
			continue

		info = pec_info[pec_name]
		pct = _compute_pct(row)
		if pct is None:
			continue

		bucket = buckets.get(pec_name)
		if not bucket:
			bucket = Bucket(
				program_enrollment=info["program_enrollment"],
				program_enrollment_course=pec_name,
				student=info["student"],
				course=info["course"],
				school=info["school"],
				academic_year=info["academic_year"],
				program=info["program"],
				grade_scale=tmeta.grade_scale,
				pct_values=[],
			)
			buckets[pec_name] = bucket

		if not bucket.grade_scale and tmeta.grade_scale:
			bucket.grade_scale = tmeta.grade_scale

		bucket.pct_values.append(pct)

	updated = 0
	created = 0

	for pec_name, bucket in buckets.items():
		if not bucket.pct_values:
			continue

		avg_pct = sum(bucket.pct_values) / len(bucket.pct_values)
		grade_value = _compute_grade_value(avg_pct, bucket.grade_scale)

		existing_name = frappe.db.get_value(
			"Course Term Result",
			{
				"reporting_cycle": rc.name,
				"program_enrollment_course": bucket.program_enrollment_course,
			},
			"name",
		)

		if existing_name:
			doc = frappe.get_doc("Course Term Result", existing_name)
			is_new = False
		else:
			doc = frappe.new_doc("Course Term Result")
			is_new = True

		doc.reporting_cycle = rc.name
		doc.student = bucket.student
		doc.program_enrollment = bucket.program_enrollment
		doc.program_enrollment_course = bucket.program_enrollment_course
		doc.course = bucket.course
		doc.school = bucket.school
		doc.academic_year = bucket.academic_year
		doc.term = rc.term
		doc.grade_scale = bucket.grade_scale

		doc.numeric_score = avg_pct
		doc.grade_value = grade_value
		doc.tasks_counted = len(bucket.pct_values)
		doc.total_weight = 1.0

		doc.calculated_on = now_datetime()
		doc.calculated_by = frappe.session.user

		doc.is_override = 1 if doc.override_grade_value else 0

		doc.save(ignore_permissions=True)
		if is_new:
			created += 1
		else:
			updated += 1

	return {
		"updated": updated,
		"created": created,
		"buckets": len(buckets),
	}


@frappe.whitelist()
def generate_student_term_reports(reporting_cycle: str):
	"""Create / update Student Term Report docs from Course Term Result for a cycle."""
	rc = _load_reporting_cycle(reporting_cycle)

	ctr_rows = frappe.get_all(
		"Course Term Result",
		filters={"reporting_cycle": rc.name},
		fields=[
			"name",
			"student",
			"program_enrollment",
			"course",
			"grade_value",
			"numeric_score",
			"override_grade_value",
			"teacher_comment",
			"is_override",
		],
		order_by="student asc, course asc",
	)
	if not ctr_rows:
		return {"reports": 0}

	# Preload Program Enrollment meta
	pe_names = {r.program_enrollment for r in ctr_rows if r.program_enrollment}
	pe_meta = {}
	if pe_names:
		pe_rows = frappe.get_all(
			"Program Enrollment",
			filters={"name": ("in", list(pe_names))},
			fields=["name", "student", "program", "academic_year", "school"],
		)
		pe_meta = {r.name: r for r in pe_rows}

	# Preload Course names
	course_names = {r.course for r in ctr_rows if r.course}
	course_meta = {}
	if course_names:
		c_rows = frappe.get_all(
			"Course",
			filters={"name": ("in", list(course_names))},
			fields=["name", "course_name"],
		)
		course_meta = {r.name: r for r in c_rows}

	# Group CTR rows by (student, program_enrollment)
	grouped: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
	for r in ctr_rows:
		key = (r.student, r.program_enrollment)
		grouped[key].append(r)

	report_count = 0

	for (student, pe_name), rows in grouped.items():
		if not pe_name:
			continue

		existing_name = frappe.db.get_value(
			"Student Term Report",
			{"reporting_cycle": rc.name, "student": student, "program_enrollment": pe_name},
			"name",
		)

		if existing_name:
			report = frappe.get_doc("Student Term Report", existing_name)
			is_new = False
		else:
			report = frappe.new_doc("Student Term Report")
			is_new = True

		report.reporting_cycle = rc.name
		report.student = student
		report.program_enrollment = pe_name

		pe = pe_meta.get(pe_name)
		if pe:
			report.program = pe.program
			report.academic_year = pe.academic_year
			report.school = pe.school

		report.term = rc.term

		# Rebuild child table from CTR rows
		report.set("courses", [])
		for r in rows:
			course_row = report.append("courses", {})
			course_row.course_term_result = r.name
			course_row.course = r.course
			c = course_meta.get(r.course)
			course_row.course_name = getattr(c, "course_name", None) if c else None
			course_row.grade_value = r.override_grade_value or r.grade_value
			course_row.numeric_score = r.numeric_score
			course_row.is_override = 1 if r.override_grade_value else 0
			course_row.teacher_comment = r.teacher_comment

		report.save(ignore_permissions=True)
		report_count += 1

	return {"reports": report_count}
