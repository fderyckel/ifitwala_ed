# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/term_reporting.py

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime
from frappe.utils.caching import redis_cache


@dataclass
class OutcomeRow:
	name: str
	student: str
	course: str
	program: Optional[str]
	task_delivery: str
	grading_mode: Optional[str]
	rubric_scoring_strategy: Optional[str]
	official_score: Optional[float]
	official_grade_value: Optional[float]
	grade_scale: Optional[str]
	procedural_status: Optional[str]
	due_date: Optional[str]
	lock_date: Optional[str]


@dataclass
class AggregateRow:
	student: str
	program_enrollment: str
	course: str
	program: Optional[str]
	academic_year: Optional[str]
	school: Optional[str]
	grade_scale: Optional[str]
	numeric_total: float
	scored_weight: float
	task_counted: int
	note_flags: List[str]
	grade_scale_conflict: bool


def get_cycle_context(reporting_cycle: str) -> dict:
	rc = frappe.get_doc("Reporting Cycle", reporting_cycle)
	if not (rc.school and rc.academic_year and rc.term):
		frappe.throw(_("Reporting Cycle must have School, Academic Year and Term set."))

	if rc.status not in ("Open", "Calculated", "Locked", "Published"):
		frappe.throw(_("Reporting Cycle status must allow calculation."))

	return {
		"name": rc.name,
		"school": rc.school,
		"academic_year": rc.academic_year,
		"term": rc.term,
		"program": getattr(rc, "program", None),
		"task_cutoff_date": rc.task_cutoff_date,
		"released_rule": rc.released_rule or "Released Only",
		"absent_policy": rc.absent_policy or "Exclude",
		"dishonesty_policy": rc.dishonesty_policy or "Force Zero",
		"exclude_excused": int(rc.exclude_excused or 0) == 1,
	}


def get_eligible_outcomes(ctx: dict) -> List[OutcomeRow]:
	filters = [
		"o.school = %(school)s",
		"o.academic_year = %(academic_year)s",
		"o.course IS NOT NULL",
	]
	params = {
		"school": ctx["school"],
		"academic_year": ctx["academic_year"],
	}
	if ctx.get("program"):
		filters.append("o.program = %(program)s")
		params["program"] = ctx["program"]

	if ctx.get("released_rule") == "Released Only":
		filters.append("o.grading_status = 'Released'")
	else:
		filters.append("o.grading_status IN ('Finalized', 'Released')")

	cutoff = ctx.get("task_cutoff_date")
	if cutoff:
		cutoff_date = getdate(cutoff)
		params["cutoff"] = cutoff_date
		filters.append(
			"(d.due_date <= %(cutoff)s OR (d.due_date IS NULL AND d.lock_date <= %(cutoff)s))"
		)

	query = f"""
		SELECT
			o.name,
			o.student,
			o.course,
			o.program,
			o.task_delivery,
			d.grading_mode,
			d.rubric_scoring_strategy,
			o.official_score,
			o.official_grade_value,
			o.grade_scale,
			o.procedural_status,
			d.due_date,
			d.lock_date
		FROM `tabTask Outcome` o
		INNER JOIN `tabTask Delivery` d ON d.name = o.task_delivery
		WHERE {' AND '.join(filters)}
	"""

	rows = frappe.db.sql(query, params, as_dict=True)
	return [
		OutcomeRow(
			name=row.name,
			student=row.student,
			course=row.course,
			program=row.program,
			task_delivery=row.task_delivery,
			grading_mode=row.grading_mode,
			rubric_scoring_strategy=row.rubric_scoring_strategy,
			official_score=row.official_score,
			official_grade_value=row.official_grade_value,
			grade_scale=row.grade_scale,
			procedural_status=row.procedural_status,
			due_date=row.due_date,
			lock_date=row.lock_date,
		)
		for row in rows
	]


def _load_program_enrollments(ctx: dict) -> Dict[str, dict]:
	filters = {
		"academic_year": ctx["academic_year"],
		"school": ctx["school"],
	}
	if ctx.get("program"):
		filters["program"] = ctx["program"]

	rows = frappe.get_all(
		"Program Enrollment",
		filters=filters,
		fields=["name", "student", "program", "academic_year", "school"],
	)
	return {row.name: row for row in rows}


def _load_program_enrollment_courses(pe_by_name: Dict[str, dict]) -> Dict[Tuple[str, str], dict]:
	if not pe_by_name:
		return {}

	pe_names = list(pe_by_name.keys())
	rows = frappe.get_all(
		"Program Enrollment Course",
		filters={"parent": ("in", pe_names)},
		fields=["parent", "course"],
	)

	pe_by_student_course: Dict[Tuple[str, str], dict] = {}
	for row in rows:
		pe = pe_by_name.get(row.parent)
		if not pe:
			continue
		key = (pe.student, row.course)
		pe_by_student_course.setdefault(
			key,
			{
				"program_enrollment": row.parent,
				"student": pe.student,
				"course": row.course,
				"program": pe.program,
				"academic_year": pe.academic_year,
				"school": pe.school,
			},
		)

	return pe_by_student_course


def aggregate_outcomes_to_course_results(ctx: dict, outcomes: Iterable[OutcomeRow]) -> Dict[Tuple[str, str], AggregateRow]:
	pe_by_name = _load_program_enrollments(ctx)
	pe_by_student_course = _load_program_enrollment_courses(pe_by_name)

	aggregates: Dict[Tuple[str, str], AggregateRow] = {}

	for outcome in outcomes:
		info = pe_by_student_course.get((outcome.student, outcome.course))
		if not info:
			continue

		key = (info["program_enrollment"], outcome.course)
		aggregate = aggregates.get(key)
		if not aggregate:
			aggregate = AggregateRow(
				student=info["student"],
				program_enrollment=info["program_enrollment"],
				course=info["course"],
				program=info["program"],
				academic_year=info["academic_year"],
				school=info["school"],
				grade_scale=None,
				numeric_total=0.0,
				scored_weight=0.0,
				task_counted=0,
				note_flags=[],
				grade_scale_conflict=False,
			)
			aggregates[key] = aggregate

		apply_result = _apply_procedural_policy(outcome, ctx)
		if not apply_result:
			continue

		numeric_value, weight, note = apply_result
		aggregate.task_counted += 1

		if weight > 0:
			aggregate.numeric_total += numeric_value
			aggregate.scored_weight += weight

		if note:
			aggregate.note_flags.append(note)

		if outcome.grade_scale:
			if not aggregate.grade_scale:
				aggregate.grade_scale = outcome.grade_scale
			elif aggregate.grade_scale != outcome.grade_scale:
				aggregate.grade_scale_conflict = True

	return aggregates


def _apply_procedural_policy(outcome: OutcomeRow, ctx: dict):
	status = (outcome.procedural_status or "").strip()
	if status == "None":
		status = ""

	numeric_value, weight, note = _score_for_outcome(outcome)

	if status == "Excused" and ctx.get("exclude_excused", True):
		return None

	if status == "Academic Dishonesty":
		if ctx.get("dishonesty_policy") == "Exclude":
			return None
		return 0.0, 1.0, "Dishonesty forced zero"

	if status == "Absent":
		absent_policy = ctx.get("absent_policy")
		if absent_policy == "Exclude":
			return None
		if absent_policy == "Count as Zero":
			return 0.0, 1.0, None
		if absent_policy == "Include as Missing":
			# Counted but does not affect numeric score.
			return 0.0, 0.0, "Absent (missing)"

	if numeric_value is None:
		if note:
			return 0.0, 0.0, note
		return None

	return numeric_value, weight, note


def _score_for_outcome(outcome: OutcomeRow):
	if (outcome.grading_mode or "").strip() == "Criteria":
		strategy = (outcome.rubric_scoring_strategy or "Sum Total").strip() or "Sum Total"
		if strategy == "Sum Total":
			return _numeric_value_from_outcome(outcome), 1.0, None

		criteria_rows = _load_outcome_criteria_points(outcome.name)
		note = "Criteria-only outcome"
		if not criteria_rows:
			note = "Criteria-only outcome (no criterion scores)"
		return 0.0, 0.0, note

	return _numeric_value_from_outcome(outcome), 1.0, None


def _numeric_value_from_outcome(outcome: OutcomeRow) -> Optional[float]:
	if outcome.official_score not in (None, ""):
		try:
			return float(outcome.official_score)
		except Exception:
			return None
	if outcome.official_grade_value not in (None, ""):
		try:
			return float(outcome.official_grade_value)
		except Exception:
			return None
	return None


def _load_outcome_criteria_points(outcome_id: str):
	if not outcome_id:
		return []
	return frappe.db.get_values(
		"Task Outcome Criterion",
		{
			"parent": outcome_id,
			"parenttype": "Task Outcome",
			"parentfield": "official_criteria",
		},
		["assessment_criteria", "level_points"],
		as_dict=True,
	) or []


@redis_cache(ttl=86400)
def _grade_scale_intervals(grade_scale: str) -> List[Tuple[float, str]]:
	rows = frappe.db.get_values(
		"Grade Scale Interval",
		{"parent": grade_scale, "parenttype": "Grade Scale"},
		["boundary_interval", "grade_code"],
		as_dict=True,
	)
	intervals: List[Tuple[float, str]] = []
	for row in rows:
		code = (row.get("grade_code") or "").strip()
		if not code:
			continue
		try:
			boundary = float(row.get("boundary_interval") or 0)
		except Exception:
			boundary = 0.0
		intervals.append((boundary, code))

	return sorted(intervals, key=lambda item: item[0])


def _grade_label_from_score(grade_scale: Optional[str], numeric_score: Optional[float]) -> Optional[str]:
	if numeric_score is None or not grade_scale:
		return None

	intervals = _grade_scale_intervals(grade_scale)
	if not intervals:
		return None

	label = None
	for boundary, code in intervals:
		if numeric_score >= boundary:
			label = code
	return label


def upsert_course_term_results(ctx: dict, aggregates: Dict[Tuple[str, str], AggregateRow]):
	existing_rows = frappe.get_all(
		"Course Term Result",
		filters={"reporting_cycle": ctx["name"]},
		fields=[
			"name",
			"student",
			"program_enrollment",
			"course",
			"numeric_score",
			"grade_value",
			"grade_scale",
			"task_counted",
			"total_weight",
			"internal_note",
			"program",
			"academic_year",
			"school",
		],
	)

	existing_by_key = {
		(row.program_enrollment, row.course): row for row in existing_rows if row.program_enrollment and row.course
	}

	updated = 0
	created = 0

	for key, aggregate in aggregates.items():
		numeric_score = (
			aggregate.numeric_total / aggregate.scored_weight
			if aggregate.scored_weight > 0
			else None
		)
		grade_scale = None if aggregate.grade_scale_conflict else aggregate.grade_scale
		grade_value = _grade_label_from_score(grade_scale, numeric_score)

		note_flags = list(aggregate.note_flags)
		if aggregate.grade_scale_conflict:
			note_flags.append("Grade scale mismatch")
		internal_note = "; ".join(sorted(set(flag for flag in note_flags if flag)))

		payload = {
			"reporting_cycle": ctx["name"],
			"student": aggregate.student,
			"program_enrollment": aggregate.program_enrollment,
			"course": aggregate.course,
			"program": aggregate.program,
			"academic_year": aggregate.academic_year,
			"school": aggregate.school,
			"term": ctx["term"],
			"grade_scale": grade_scale,
			"numeric_score": numeric_score,
			"grade_value": grade_value,
			"task_counted": aggregate.task_counted,
			"total_weight": aggregate.scored_weight,
			"internal_note": internal_note or None,
		}

		existing = existing_by_key.get(key)
		if existing:
			changed = False
			for field, value in payload.items():
				if getattr(existing, field, None) != value:
					changed = True
					break
			if not changed:
				continue

			doc = frappe.get_doc("Course Term Result", existing.name)
			for field, value in payload.items():
				setattr(doc, field, value)
			doc.calculated_on = now_datetime()
			doc.calculated_by = frappe.session.user
			doc.save(ignore_permissions=True)
			updated += 1
		else:
			doc = frappe.new_doc("Course Term Result")
			for field, value in payload.items():
				setattr(doc, field, value)
			doc.calculated_on = now_datetime()
			doc.calculated_by = frappe.session.user
			doc.save(ignore_permissions=True)
			created += 1

	remaining_keys = set(existing_by_key.keys()) - set(aggregates.keys())
	for key in remaining_keys:
		row = existing_by_key[key]
		doc = frappe.get_doc("Course Term Result", row.name)
		changed = False
		if doc.numeric_score is not None:
			doc.numeric_score = None
			changed = True
		if doc.grade_value:
			doc.grade_value = None
			changed = True
		if doc.task_counted:
			doc.task_counted = 0
			changed = True
		if doc.total_weight:
			doc.total_weight = 0
			changed = True
		if doc.internal_note != "No eligible outcomes":
			doc.internal_note = "No eligible outcomes"
			changed = True
		if changed:
			doc.calculated_on = now_datetime()
			doc.calculated_by = frappe.session.user
			doc.save(ignore_permissions=True)
			updated += 1

	return {"updated": updated, "created": created, "buckets": len(aggregates)}


@frappe.whitelist()
def recalculate_course_term_results(reporting_cycle: str):
	ctx = get_cycle_context(reporting_cycle)
	outcomes = get_eligible_outcomes(ctx)
	aggregates = aggregate_outcomes_to_course_results(ctx, outcomes)
	return upsert_course_term_results(ctx, aggregates)


@frappe.whitelist()
def generate_student_term_reports(reporting_cycle: str):
	ctx = get_cycle_context(reporting_cycle)

	ctr_rows = frappe.get_all(
		"Course Term Result",
		filters={"reporting_cycle": ctx["name"]},
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

	pe_names = {row.program_enrollment for row in ctr_rows if row.program_enrollment}
	pe_meta = {}
	if pe_names:
		pe_rows = frappe.get_all(
			"Program Enrollment",
			filters={"name": ("in", list(pe_names))},
			fields=["name", "student", "program", "academic_year", "school"],
		)
		pe_meta = {row.name: row for row in pe_rows}

	course_names = {row.course for row in ctr_rows if row.course}
	course_meta = {}
	if course_names:
		c_rows = frappe.get_all(
			"Course",
			filters={"name": ("in", list(course_names))},
			fields=["name", "course_name"],
		)
		course_meta = {row.name: row for row in c_rows}

	grouped: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
	for row in ctr_rows:
		key = (row.student, row.program_enrollment)
		grouped[key].append(row)

	report_count = 0
	for (student, pe_name), rows in grouped.items():
		if not pe_name:
			continue

		existing_name = frappe.db.get_value(
			"Student Term Report",
			{"reporting_cycle": ctx["name"], "student": student, "program_enrollment": pe_name},
			"name",
		)

		if existing_name:
			report = frappe.get_doc("Student Term Report", existing_name)
		else:
			report = frappe.new_doc("Student Term Report")

		report.reporting_cycle = ctx["name"]
		report.student = student
		report.program_enrollment = pe_name

		pe = pe_meta.get(pe_name)
		if pe:
			report.program = pe.program
			report.academic_year = pe.academic_year
			report.school = pe.school

		report.term = ctx["term"]
		report.set("courses", [])
		for row in rows:
			course_row = report.append("courses", {})
			course_row.course_term_result = row.name
			course_row.course = row.course
			course = course_meta.get(row.course)
			course_row.course_name = getattr(course, "course_name", None) if course else None
			course_row.grade_value = row.override_grade_value or row.grade_value
			course_row.numeric_score = row.numeric_score
			course_row.is_override = 1 if row.override_grade_value else 0
			course_row.teacher_comment = row.teacher_comment

		report.save(ignore_permissions=True)
		report_count += 1

	return {"reports": report_count}
