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
        filters.append("(d.due_date <= %(cutoff)s OR (d.due_date IS NULL AND d.lock_date <= %(cutoff)s))")

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
		WHERE {" AND ".join(filters)}
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


def aggregate_outcomes_to_course_results(
    ctx: dict, outcomes: Iterable[OutcomeRow]
) -> Dict[Tuple[str, str], AggregateRow]:
    pe_by_name = _load_program_enrollments(ctx)
    pe_by_student_course = _load_program_enrollment_courses(pe_by_name)
    outcome_rows = list(outcomes)
    criteria_points_by_outcome = _load_outcome_criteria_points_map(
        [
            outcome.name
            for outcome in outcome_rows
            if (outcome.grading_mode or "").strip() == "Criteria"
            and (outcome.rubric_scoring_strategy or "Sum Total").strip() != "Sum Total"
        ]
    )

    aggregates: Dict[Tuple[str, str], AggregateRow] = {}

    for outcome in outcome_rows:
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

        apply_result = _apply_procedural_policy(
            outcome,
            ctx,
            criteria_points_by_outcome=criteria_points_by_outcome,
        )
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


def _apply_procedural_policy(
    outcome: OutcomeRow,
    ctx: dict,
    *,
    criteria_points_by_outcome: Optional[Dict[str, List[dict]]] = None,
):
    status = (outcome.procedural_status or "").strip()
    if status == "None":
        status = ""

    numeric_value, weight, note = _score_for_outcome(
        outcome,
        criteria_points_by_outcome=criteria_points_by_outcome,
    )

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


def _score_for_outcome(
    outcome: OutcomeRow,
    *,
    criteria_points_by_outcome: Optional[Dict[str, List[dict]]] = None,
):
    if (outcome.grading_mode or "").strip() == "Criteria":
        strategy = (outcome.rubric_scoring_strategy or "Sum Total").strip() or "Sum Total"
        if strategy == "Sum Total":
            return _numeric_value_from_outcome(outcome), 1.0, None

        criteria_rows = (
            list((criteria_points_by_outcome or {}).get(outcome.name) or [])
            if criteria_points_by_outcome is not None
            else _load_outcome_criteria_points(outcome.name)
        )
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
    return (
        frappe.db.get_values(
            "Task Outcome Criterion",
            {
                "parent": outcome_id,
                "parenttype": "Task Outcome",
                "parentfield": "official_criteria",
            },
            ["assessment_criteria", "level_points"],
            as_dict=True,
        )
        or []
    )


def _load_outcome_criteria_points_map(outcome_ids: List[str]) -> Dict[str, List[dict]]:
    ordered_ids = []
    seen = set()
    for outcome_id in outcome_ids or []:
        normalized = (outcome_id or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered_ids.append(normalized)

    if not ordered_ids:
        return {}

    rows = frappe.get_all(
        "Task Outcome Criterion",
        filters={
            "parent": ("in", ordered_ids),
            "parenttype": "Task Outcome",
            "parentfield": "official_criteria",
        },
        fields=["parent", "assessment_criteria", "level_points"],
        order_by="parent asc, idx asc",
    )

    grouped = {outcome_id: [] for outcome_id in ordered_ids}
    for row in rows or []:
        parent = (row.get("parent") or "").strip()
        if not parent or parent not in grouped:
            continue
        grouped[parent].append(
            {
                "assessment_criteria": row.get("assessment_criteria"),
                "level_points": row.get("level_points"),
            }
        )

    return grouped


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


def _course_term_result_payload(ctx: dict, aggregate: AggregateRow) -> dict:
    numeric_score = aggregate.numeric_total / aggregate.scored_weight if aggregate.scored_weight > 0 else None
    grade_scale = None if aggregate.grade_scale_conflict else aggregate.grade_scale
    grade_value = _grade_label_from_score(grade_scale, numeric_score)

    note_flags = list(aggregate.note_flags)
    if aggregate.grade_scale_conflict:
        note_flags.append("Grade scale mismatch")
    internal_note = "; ".join(sorted(set(flag for flag in note_flags if flag)))

    return {
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


def _course_term_result_reset_payload() -> dict:
    return {
        "numeric_score": None,
        "grade_value": None,
        "task_counted": 0,
        "total_weight": 0,
        "internal_note": "No eligible outcomes",
    }


def _row_matches_payload(row, payload: dict) -> bool:
    for field, value in payload.items():
        if getattr(row, field, None) != value:
            return False
    return True


def _apply_payload_to_doc(doc, payload: dict) -> None:
    for field, value in payload.items():
        setattr(doc, field, value)


def _student_term_report_header_payload(ctx: dict, student: str, program_enrollment: str, pe_meta: dict) -> dict:
    payload = {
        "reporting_cycle": ctx["name"],
        "student": student,
        "program_enrollment": program_enrollment,
        "term": ctx["term"],
    }

    pe = pe_meta.get(program_enrollment)
    if pe:
        payload["program"] = pe.program
        payload["academic_year"] = pe.academic_year
        payload["school"] = pe.school

    return payload


def _student_term_report_course_payloads(rows: List[dict], course_meta: dict) -> List[dict]:
    payloads = []
    for row in rows:
        course = course_meta.get(row.course)
        payloads.append(
            {
                "course_term_result": row.name,
                "course": row.course,
                "course_name": getattr(course, "course_name", None) if course else None,
                "grade_value": row.override_grade_value or row.grade_value,
                "numeric_score": row.numeric_score,
                "is_override": 1 if row.override_grade_value else 0,
                "teacher_comment": row.teacher_comment,
            }
        )
    return payloads


def _load_existing_student_term_reports(reporting_cycle: str, program_enrollment_names: List[str]) -> dict:
    if not program_enrollment_names:
        return {}

    existing_rows = frappe.get_all(
        "Student Term Report",
        filters={
            "reporting_cycle": reporting_cycle,
            "program_enrollment": ("in", program_enrollment_names),
        },
        fields=[
            "name",
            "reporting_cycle",
            "student",
            "program_enrollment",
            "program",
            "academic_year",
            "school",
            "term",
        ],
    )
    if not existing_rows:
        return {}

    report_names = [row.name for row in existing_rows if row.name]
    child_rows = frappe.get_all(
        "Student Term Report Course",
        filters={
            "parent": ("in", report_names),
            "parenttype": "Student Term Report",
        },
        fields=[
            "parent",
            "course_term_result",
            "course",
            "course_name",
            "grade_value",
            "numeric_score",
            "is_override",
            "teacher_comment",
        ],
        order_by="parent asc, idx asc",
    )

    courses_by_parent: Dict[str, List[dict]] = defaultdict(list)
    for row in child_rows:
        courses_by_parent[row.parent].append(
            {
                "course_term_result": row.course_term_result,
                "course": row.course,
                "course_name": row.course_name,
                "grade_value": row.grade_value,
                "numeric_score": row.numeric_score,
                "is_override": row.is_override,
                "teacher_comment": row.teacher_comment,
            }
        )

    return {
        (row.student, row.program_enrollment): {
            "row": row,
            "courses": courses_by_parent.get(row.name, []),
        }
        for row in existing_rows
        if row.student and row.program_enrollment
    }


def _student_term_report_matches(existing_report: dict, header_payload: dict, course_payloads: List[dict]) -> bool:
    if not _row_matches_payload(existing_report["row"], header_payload):
        return False
    return existing_report.get("courses") == course_payloads


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
            "term",
        ],
    )

    existing_by_key = {
        (row.program_enrollment, row.course): row for row in existing_rows if row.program_enrollment and row.course
    }

    updated = 0
    created = 0

    for key, aggregate in aggregates.items():
        payload = _course_term_result_payload(ctx, aggregate)

        existing = existing_by_key.get(key)
        if existing:
            if _row_matches_payload(existing, payload):
                continue

            doc = frappe.get_doc("Course Term Result", existing.name)
            _apply_payload_to_doc(doc, payload)
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
        reset_payload = _course_term_result_reset_payload()
        if _row_matches_payload(row, reset_payload):
            continue

        doc = frappe.get_doc("Course Term Result", row.name)
        _apply_payload_to_doc(doc, reset_payload)
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

    existing_reports = _load_existing_student_term_reports(ctx["name"], list(pe_names))
    report_count = 0
    for (student, pe_name), rows in grouped.items():
        if not pe_name:
            continue

        header_payload = _student_term_report_header_payload(ctx, student, pe_name, pe_meta)
        course_payloads = _student_term_report_course_payloads(rows, course_meta)
        existing_report = existing_reports.get((student, pe_name))

        if existing_report and _student_term_report_matches(existing_report, header_payload, course_payloads):
            report_count += 1
            continue

        if existing_report:
            report = frappe.get_doc("Student Term Report", existing_report["row"].name)
        else:
            report = frappe.new_doc("Student Term Report")

        _apply_payload_to_doc(report, header_payload)
        report.set("courses", [])
        for payload in course_payloads:
            course_row = report.append("courses", {})
            for field, value in payload.items():
                setattr(course_row, field, value)

        report.save(ignore_permissions=True)
        report_count += 1

    return {"reports": report_count}
