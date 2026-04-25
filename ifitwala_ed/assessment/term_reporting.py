# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/term_reporting.py

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
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
    max_points: Optional[float] = None
    assessment_category: Optional[str] = None
    reporting_weight: Optional[float] = None


@dataclass
class ComponentRow:
    component_type: str
    component_key: str
    label: str
    assessment_category: Optional[str] = None
    assessment_criteria: Optional[str] = None
    weight: Optional[float] = None
    raw_score: Optional[float] = None
    weighted_score: Optional[float] = None
    grade_value: Optional[str] = None
    evidence_count: int = 0
    included_outcome_count: int = 0
    excluded_outcome_count: int = 0
    calculation_note: Optional[str] = None


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
    assessment_scheme: Optional[str] = None
    assessment_calculation_method: Optional[str] = None
    assessment_scheme_config: Optional[dict] = None
    components: List[ComponentRow] = field(default_factory=list)


def get_cycle_context(reporting_cycle: str) -> dict:
    rc = frappe.get_doc("Reporting Cycle", reporting_cycle)
    if not (rc.school and rc.academic_year and rc.term):
        frappe.throw(_("Reporting Cycle must have School, Academic Year and Term set."))

    if rc.status not in ("Open", "Calculated", "Locked", "Published"):
        frappe.throw(_("Reporting Cycle status must allow calculation."))

    ctx = {
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
        "assessment_scheme": getattr(rc, "assessment_scheme", None),
    }
    ctx["assessment_scheme_config"] = load_assessment_scheme_config(ctx.get("assessment_scheme"))
    ctx["active_assessment_scheme_configs"] = load_active_assessment_scheme_configs(ctx)
    ctx["calculation_method"] = (
        ctx["assessment_scheme_config"].get("calculation_method") if ctx["assessment_scheme_config"] else None
    )
    return ctx


def _row_value(row, fieldname: str):
    if hasattr(row, "get"):
        return row.get(fieldname)
    return getattr(row, fieldname, None)


def load_assessment_scheme_config(assessment_scheme: Optional[str]) -> Optional[dict]:
    if not assessment_scheme:
        return None

    scheme = frappe.db.get_value(
        "Assessment Scheme",
        assessment_scheme,
        [
            "name",
            "scheme_name",
            "status",
            "calculation_method",
            "default_grade_scale",
            "school",
            "academic_year",
            "program",
            "course",
        ],
        as_dict=True,
    )
    if not scheme:
        frappe.throw(_("Assessment Scheme {0} was not found.").format(assessment_scheme))

    categories_by_parent = _load_assessment_scheme_categories([assessment_scheme])
    return _assessment_scheme_config_from_row(scheme, categories_by_parent)


def load_active_assessment_scheme_configs(ctx: dict) -> List[dict]:
    rows = frappe.db.sql(
        """
        SELECT
            name,
            scheme_name,
            status,
            calculation_method,
            default_grade_scale,
            school,
            academic_year,
            program,
            course
        FROM `tabAssessment Scheme`
        WHERE status = 'Active'
            AND school = %(school)s
            AND (COALESCE(academic_year, '') = '' OR academic_year = %(academic_year)s)
            AND (%(program)s = '' OR COALESCE(program, '') = '' OR program = %(program)s)
        ORDER BY
            CASE WHEN COALESCE(course, '') = '' THEN 0 ELSE 1 END DESC,
            CASE WHEN COALESCE(program, '') = '' THEN 0 ELSE 1 END DESC,
            CASE WHEN COALESCE(academic_year, '') = '' THEN 0 ELSE 1 END DESC,
            scheme_name ASC,
            name ASC
        """,
        {
            "school": ctx["school"],
            "academic_year": ctx["academic_year"],
            "program": (ctx.get("program") or "").strip(),
        },
        as_dict=True,
    )
    scheme_names = [_row_value(row, "name") for row in rows or [] if _row_value(row, "name")]
    categories_by_parent = _load_assessment_scheme_categories(scheme_names)
    return [_assessment_scheme_config_from_row(row, categories_by_parent) for row in rows or []]


def _load_assessment_scheme_categories(scheme_names: List[str]) -> Dict[str, List[dict]]:
    if not scheme_names:
        return {}

    category_rows = frappe.get_all(
        "Assessment Scheme Category",
        filters={
            "parent": ("in", scheme_names),
            "parenttype": "Assessment Scheme",
            "parentfield": "categories",
        },
        fields=[
            "parent",
            "assessment_category",
            "weight",
            "active",
            "include_in_term_report",
            "include_in_final_grade",
            "report_label",
            "sort_order",
        ],
        order_by="sort_order asc, idx asc",
        limit=0,
    )

    categories_by_parent: Dict[str, List[dict]] = defaultdict(list)
    for row in category_rows or []:
        parent = (_row_value(row, "parent") or "").strip()
        category = (_row_value(row, "assessment_category") or "").strip()
        if not category:
            continue
        categories_by_parent[parent].append(
            {
                "assessment_category": category,
                "weight": _coerce_float(_row_value(row, "weight"), default=0.0),
                "active": int(_row_value(row, "active") or 0) == 1,
                "include_in_term_report": int(_row_value(row, "include_in_term_report") or 0) == 1,
                "include_in_final_grade": int(_row_value(row, "include_in_final_grade") or 0) == 1,
                "report_label": (_row_value(row, "report_label") or category).strip(),
                "sort_order": int(_row_value(row, "sort_order") or 0),
            }
        )
    return categories_by_parent


def _assessment_scheme_config_from_row(row, categories_by_parent: Dict[str, List[dict]]) -> dict:
    scheme_name = _row_value(row, "name")
    return {
        "name": scheme_name,
        "scheme_name": _row_value(row, "scheme_name"),
        "status": _row_value(row, "status"),
        "calculation_method": _row_value(row, "calculation_method") or "Weighted Tasks",
        "default_grade_scale": _row_value(row, "default_grade_scale"),
        "school": _row_value(row, "school"),
        "academic_year": _row_value(row, "academic_year"),
        "program": _row_value(row, "program"),
        "course": _row_value(row, "course"),
        "categories": categories_by_parent.get(scheme_name, []),
    }


def _coerce_float(value, *, default: Optional[float] = None) -> Optional[float]:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except Exception:
        return default


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
			d.max_points,
			d.assessment_category,
			d.reporting_weight,
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
            max_points=row.max_points,
            assessment_category=row.assessment_category,
            reporting_weight=row.reporting_weight,
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


def _new_aggregate(info: dict) -> AggregateRow:
    return AggregateRow(
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


def _record_grade_scale(aggregate: AggregateRow, outcome: OutcomeRow) -> None:
    if not outcome.grade_scale:
        return
    if not aggregate.grade_scale:
        aggregate.grade_scale = outcome.grade_scale
    elif aggregate.grade_scale != outcome.grade_scale:
        aggregate.grade_scale_conflict = True


def _scheme_method(scheme_config: Optional[dict]) -> Optional[str]:
    scheme = scheme_config or {}
    return (scheme.get("calculation_method") or "").strip() or None


def _scheme_category_rule_map(scheme_config: Optional[dict]) -> dict:
    scheme = scheme_config or {}
    return {
        row.get("assessment_category"): row
        for row in (scheme.get("categories") or [])
        if row.get("assessment_category") and row.get("active")
    }


def _scheme_scope_matches(scheme_config: dict, info: dict, ctx: dict) -> bool:
    scope_values = {
        "school": info.get("school") or ctx.get("school"),
        "academic_year": info.get("academic_year") or ctx.get("academic_year"),
        "program": info.get("program") or ctx.get("program"),
        "course": info.get("course"),
    }
    for fieldname, value in scope_values.items():
        scheme_value = (scheme_config.get(fieldname) or "").strip()
        if scheme_value and scheme_value != (value or ""):
            return False
    return True


def _scheme_specificity(scheme_config: dict, default_scheme: Optional[str]) -> Tuple[int, str]:
    score = 0
    if scheme_config.get("academic_year"):
        score += 2
    if scheme_config.get("program"):
        score += 4
    if scheme_config.get("course"):
        score += 8
    if default_scheme and scheme_config.get("name") == default_scheme:
        score += 1
    return score, scheme_config.get("name") or ""


def _resolve_assessment_scheme_config(ctx: dict, info: dict) -> Optional[dict]:
    default_scheme = ctx.get("assessment_scheme")
    candidates_by_name = {}
    for scheme_config in ctx.get("active_assessment_scheme_configs") or []:
        if _scheme_scope_matches(scheme_config, info, ctx):
            candidates_by_name[scheme_config.get("name")] = scheme_config

    default_config = ctx.get("assessment_scheme_config")
    if default_config and _scheme_scope_matches(default_config, info, ctx):
        candidates_by_name[default_config.get("name")] = default_config

    if not candidates_by_name:
        return None

    return sorted(
        candidates_by_name.values(),
        key=lambda scheme: _scheme_specificity(scheme, default_scheme),
        reverse=True,
    )[0]


def _reporting_weight(outcome: OutcomeRow) -> float:
    weight = _coerce_float(outcome.reporting_weight, default=1.0)
    if weight is None or weight <= 0:
        return 1.0
    return weight


def _component_payload(
    *,
    component_type: str,
    component_key: str,
    label: str,
    assessment_category: Optional[str] = None,
    assessment_criteria: Optional[str] = None,
    weight: Optional[float] = None,
    raw_score: Optional[float] = None,
    weighted_score: Optional[float] = None,
    evidence_count: int = 0,
    included_outcome_count: int = 0,
    excluded_outcome_count: int = 0,
    calculation_note: Optional[str] = None,
) -> ComponentRow:
    return ComponentRow(
        component_type=component_type,
        component_key=component_key,
        label=label,
        assessment_category=assessment_category,
        assessment_criteria=assessment_criteria,
        weight=weight,
        raw_score=raw_score,
        weighted_score=weighted_score,
        evidence_count=evidence_count,
        included_outcome_count=included_outcome_count,
        excluded_outcome_count=excluded_outcome_count,
        calculation_note=calculation_note,
    )


def aggregate_outcomes_to_course_results(
    ctx: dict, outcomes: Iterable[OutcomeRow]
) -> Dict[Tuple[str, str], AggregateRow]:
    pe_by_name = _load_program_enrollments(ctx)
    pe_by_student_course = _load_program_enrollment_courses(pe_by_name)
    outcome_rows = list(outcomes)
    scheme_configs = [ctx.get("assessment_scheme_config"), *(ctx.get("active_assessment_scheme_configs") or [])]
    criteria_based_enabled = any(_scheme_method(scheme_config) == "Criteria-Based" for scheme_config in scheme_configs)
    criteria_points_by_outcome = _load_outcome_criteria_points_map(
        [
            outcome.name
            for outcome in outcome_rows
            if (outcome.grading_mode or "").strip() == "Criteria"
            and (criteria_based_enabled or (outcome.rubric_scoring_strategy or "Sum Total").strip() != "Sum Total")
        ]
    )

    aggregates: Dict[Tuple[str, str], AggregateRow] = {}
    grouped_items: Dict[Tuple[str, str], List[Tuple[OutcomeRow, float, float, Optional[str]]]] = defaultdict(list)
    info_by_key: Dict[Tuple[str, str], dict] = {}

    for outcome in outcome_rows:
        info = pe_by_student_course.get((outcome.student, outcome.course))
        if not info:
            continue

        key = (info["program_enrollment"], outcome.course)
        info_by_key[key] = info
        apply_result = _apply_procedural_policy(
            outcome,
            ctx,
            criteria_points_by_outcome=criteria_points_by_outcome,
        )
        if not apply_result:
            continue

        numeric_value, weight, note = apply_result
        grouped_items[key].append((outcome, numeric_value, weight, note))

    for key, items in grouped_items.items():
        aggregate = _new_aggregate(info_by_key[key])
        scheme_config = _resolve_assessment_scheme_config(ctx, info_by_key[key])
        aggregate.assessment_scheme_config = scheme_config
        aggregate.assessment_scheme = (scheme_config or {}).get("name")
        aggregate.assessment_calculation_method = _scheme_method(scheme_config)
        method = aggregate.assessment_calculation_method
        aggregates[key] = aggregate

        if method in ("Weighted Categories", "Category + Task Weight Hybrid"):
            _apply_category_method_aggregate(
                aggregate, items, scheme_config, use_task_weights=method.endswith("Hybrid")
            )
        elif method == "Total Points":
            _apply_total_points_aggregate(aggregate, items)
        elif method == "Weighted Tasks":
            _apply_weighted_tasks_aggregate(aggregate, items, use_task_weights=True)
        elif method == "Criteria-Based":
            _apply_criteria_based_aggregate(aggregate, items, criteria_points_by_outcome)
        elif method == "Manual Final":
            _apply_manual_final_aggregate(aggregate, items)
        else:
            _apply_weighted_tasks_aggregate(aggregate, items, use_task_weights=False)

        for outcome, _numeric_value, _weight, note in items:
            _record_grade_scale(aggregate, outcome)
            if note:
                aggregate.note_flags.append(note)

    return aggregates


def _apply_weighted_tasks_aggregate(
    aggregate: AggregateRow,
    items: List[Tuple[OutcomeRow, float, float, Optional[str]]],
    *,
    use_task_weights: bool,
) -> None:
    for outcome, numeric_value, weight, _note in items:
        aggregate.task_counted += 1
        if weight <= 0:
            continue
        resolved_weight = _reporting_weight(outcome) if use_task_weights else weight
        aggregate.numeric_total += numeric_value * resolved_weight
        aggregate.scored_weight += resolved_weight
        if use_task_weights:
            aggregate.components.append(
                _component_payload(
                    component_type="Task",
                    component_key=outcome.task_delivery,
                    label=outcome.task_delivery,
                    assessment_category=outcome.assessment_category,
                    weight=resolved_weight,
                    raw_score=numeric_value,
                    weighted_score=numeric_value * resolved_weight,
                    evidence_count=1,
                    included_outcome_count=1,
                )
            )


def _apply_total_points_aggregate(
    aggregate: AggregateRow,
    items: List[Tuple[OutcomeRow, float, float, Optional[str]]],
) -> None:
    earned = 0.0
    possible = 0.0
    excluded = 0
    included = 0

    for outcome, numeric_value, weight, _note in items:
        aggregate.task_counted += 1
        max_points = _coerce_float(outcome.max_points, default=None)
        if weight <= 0:
            excluded += 1
            continue
        if max_points is None or max_points <= 0:
            excluded += 1
            aggregate.note_flags.append("Outcome missing max points for total-points calculation")
            continue
        earned += numeric_value
        possible += max_points
        included += 1

    aggregate.numeric_total = earned * 100.0
    aggregate.scored_weight = possible
    raw_score = (earned / possible) * 100.0 if possible > 0 else None
    aggregate.components.append(
        _component_payload(
            component_type="Summary",
            component_key="total_points",
            label="Total Points",
            weight=possible,
            raw_score=raw_score,
            weighted_score=earned,
            evidence_count=included + excluded,
            included_outcome_count=included,
            excluded_outcome_count=excluded,
            calculation_note="Earned points divided by possible points.",
        )
    )


def _apply_category_method_aggregate(
    aggregate: AggregateRow,
    items: List[Tuple[OutcomeRow, float, float, Optional[str]]],
    scheme_config: Optional[dict],
    *,
    use_task_weights: bool,
) -> None:
    rules = _scheme_category_rule_map(scheme_config)
    buckets: dict = defaultdict(
        lambda: {
            "numeric_total": 0.0,
            "scored_weight": 0.0,
            "included": 0,
            "excluded": 0,
            "rule": None,
        }
    )

    for outcome, numeric_value, weight, _note in items:
        aggregate.task_counted += 1
        category = (outcome.assessment_category or "").strip()
        rule = rules.get(category)
        if not category or not rule or not rule.get("include_in_term_report"):
            aggregate.note_flags.append("Outcome excluded from category scheme")
            continue
        bucket = buckets[category]
        bucket["rule"] = rule
        if weight <= 0 or not rule.get("include_in_final_grade"):
            bucket["excluded"] += 1
            continue
        resolved_weight = _reporting_weight(outcome) if use_task_weights else weight
        bucket["numeric_total"] += numeric_value * resolved_weight
        bucket["scored_weight"] += resolved_weight
        bucket["included"] += 1

    for category, bucket in sorted(
        buckets.items(),
        key=lambda item: ((item[1].get("rule") or {}).get("sort_order") or 0, item[0]),
    ):
        rule = bucket.get("rule") or {}
        category_score = bucket["numeric_total"] / bucket["scored_weight"] if bucket["scored_weight"] > 0 else None
        category_weight = _coerce_float(rule.get("weight"), default=0.0) or 0.0
        if category_score is not None and rule.get("include_in_final_grade") and category_weight > 0:
            aggregate.numeric_total += category_score * category_weight
            aggregate.scored_weight += category_weight
        aggregate.components.append(
            _component_payload(
                component_type="Category",
                component_key=category,
                label=rule.get("report_label") or category,
                assessment_category=category,
                weight=category_weight,
                raw_score=category_score,
                weighted_score=category_score * category_weight if category_score is not None else None,
                evidence_count=bucket["included"] + bucket["excluded"],
                included_outcome_count=bucket["included"],
                excluded_outcome_count=bucket["excluded"],
            )
        )


def _apply_criteria_based_aggregate(
    aggregate: AggregateRow,
    items: List[Tuple[OutcomeRow, float, float, Optional[str]]],
    criteria_points_by_outcome: Dict[str, List[dict]],
) -> None:
    criteria_buckets: dict = defaultdict(lambda: {"total": 0.0, "count": 0})

    for outcome, _numeric_value, weight, note in items:
        aggregate.task_counted += 1
        if note == "Absent (missing)":
            continue
        rows = criteria_points_by_outcome.get(outcome.name) or []
        if weight <= 0 and not rows:
            continue
        for row in rows:
            criteria = (row.get("assessment_criteria") or "").strip()
            if not criteria:
                continue
            points = _coerce_float(row.get("level_points"), default=None)
            if points is None:
                continue
            criteria_buckets[criteria]["total"] += points
            criteria_buckets[criteria]["count"] += 1

    for criteria, bucket in sorted(criteria_buckets.items()):
        if bucket["count"] <= 0:
            continue
        average = bucket["total"] / bucket["count"]
        aggregate.numeric_total += average
        aggregate.scored_weight += 1.0
        aggregate.components.append(
            _component_payload(
                component_type="Criterion",
                component_key=criteria,
                label=criteria,
                assessment_criteria=criteria,
                weight=1.0,
                raw_score=average,
                weighted_score=average,
                evidence_count=bucket["count"],
                included_outcome_count=bucket["count"],
            )
        )

    if not criteria_buckets:
        aggregate.note_flags.append("Criteria-based scheme found no criterion scores")


def _apply_manual_final_aggregate(
    aggregate: AggregateRow,
    items: List[Tuple[OutcomeRow, float, float, Optional[str]]],
) -> None:
    aggregate.task_counted = len(items)
    aggregate.numeric_total = 0.0
    aggregate.scored_weight = 0.0
    aggregate.note_flags.append("Manual final scheme; enter final result through the governed override path")
    aggregate.components.append(
        _component_payload(
            component_type="Manual",
            component_key="manual_final",
            label="Manual Final",
            evidence_count=len(items),
            included_outcome_count=0,
            excluded_outcome_count=len(items),
            calculation_note="Evidence is listed for review; final grade is entered manually.",
        )
    )


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
        criteria_rows = (
            list((criteria_points_by_outcome or {}).get(outcome.name) or [])
            if criteria_points_by_outcome is not None
            else None
        )
        if strategy == "Sum Total":
            numeric_value = _numeric_value_from_outcome(outcome)
            if numeric_value is None and criteria_rows:
                return 0.0, 0.0, "Criteria-only outcome"
            return numeric_value, 1.0, None

        criteria_rows = criteria_rows if criteria_rows is not None else _load_outcome_criteria_points(outcome.name)
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
    scheme = aggregate.assessment_scheme_config or ctx.get("assessment_scheme_config") or {}
    grade_scale = None if aggregate.grade_scale_conflict else aggregate.grade_scale or scheme.get("default_grade_scale")
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


def _component_rows_payload(aggregate: AggregateRow, grade_scale: Optional[str]) -> List[dict]:
    payload = []
    for component in aggregate.components or []:
        raw_score = component.raw_score
        grade_value = component.grade_value
        if not grade_value and raw_score is not None:
            grade_value = _grade_label_from_score(grade_scale, raw_score)
        payload.append(
            {
                "component_type": component.component_type,
                "component_key": component.component_key,
                "label": component.label,
                "assessment_category": component.assessment_category,
                "assessment_criteria": component.assessment_criteria,
                "weight": component.weight,
                "raw_score": component.raw_score,
                "weighted_score": component.weighted_score,
                "grade_value": grade_value,
                "evidence_count": component.evidence_count,
                "included_outcome_count": component.included_outcome_count,
                "excluded_outcome_count": component.excluded_outcome_count,
                "calculation_note": component.calculation_note,
            }
        )
    return payload


def _component_rows_match(existing_rows, payload: List[dict]) -> bool:
    normalized_existing = []
    for row in existing_rows or []:
        normalized_existing.append({field: _row_value(row, field) for field in payload[0].keys()} if payload else {})
    return normalized_existing == payload


def _set_component_rows(doc, component_payloads: List[dict]) -> None:
    if not hasattr(doc, "set"):
        return
    doc.set("components", [])
    for payload in component_payloads or []:
        row = doc.append("components", {})
        for fieldname, value in payload.items():
            setattr(row, fieldname, value)


def _load_existing_course_term_result_components(result_names: List[str]) -> dict:
    if not result_names:
        return {}
    rows = frappe.get_all(
        "Course Term Result Component",
        filters={
            "parent": ("in", result_names),
            "parenttype": "Course Term Result",
            "parentfield": "components",
        },
        fields=[
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
        ],
        order_by="parent asc, idx asc",
    )
    grouped: Dict[str, List[dict]] = defaultdict(list)
    for row in rows or []:
        grouped[_row_value(row, "parent")].append(row)
    return grouped


def _course_term_result_reset_payload() -> dict:
    return {
        "numeric_score": None,
        "grade_value": None,
        "task_counted": 0,
        "total_weight": 0,
        "internal_note": "No eligible outcomes",
    }


def _row_matches_payload(row, payload: dict) -> bool:
    for fieldname, value in payload.items():
        if getattr(row, fieldname, None) != value:
            return False
    return True


def _apply_payload_to_doc(doc, payload: dict) -> None:
    for fieldname, value in payload.items():
        setattr(doc, fieldname, value)


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
    existing_components = _load_existing_course_term_result_components(
        [row.name for row in existing_rows if getattr(row, "name", None)]
    )

    updated = 0
    created = 0

    for key, aggregate in aggregates.items():
        payload = _course_term_result_payload(ctx, aggregate)
        component_payloads = _component_rows_payload(aggregate, payload.get("grade_scale"))

        existing = existing_by_key.get(key)
        if existing:
            if _row_matches_payload(existing, payload) and _component_rows_match(
                existing_components.get(existing.name, []),
                component_payloads,
            ):
                continue

            doc = frappe.get_doc("Course Term Result", existing.name)
            _apply_payload_to_doc(doc, payload)
            _set_component_rows(doc, component_payloads)
            doc.calculated_on = now_datetime()
            doc.calculated_by = frappe.session.user
            doc.save(ignore_permissions=True)
            updated += 1
        else:
            doc = frappe.new_doc("Course Term Result")
            for field, value in payload.items():
                setattr(doc, field, value)
            _set_component_rows(doc, component_payloads)
            doc.calculated_on = now_datetime()
            doc.calculated_by = frappe.session.user
            doc.save(ignore_permissions=True)
            created += 1

    remaining_keys = set(existing_by_key.keys()) - set(aggregates.keys())
    for key in remaining_keys:
        row = existing_by_key[key]
        reset_payload = _course_term_result_reset_payload()
        if _row_matches_payload(row, reset_payload) and _component_rows_match(
            existing_components.get(row.name, []), []
        ):
            continue

        doc = frappe.get_doc("Course Term Result", row.name)
        _apply_payload_to_doc(doc, reset_payload)
        _set_component_rows(doc, [])
        doc.calculated_on = now_datetime()
        doc.calculated_by = frappe.session.user
        doc.save(ignore_permissions=True)
        updated += 1

    return {"updated": updated, "created": created, "buckets": len(aggregates)}


@frappe.whitelist()
def recalculate_course_term_results(reporting_cycle: str):
    ctx = get_cycle_context(reporting_cycle)
    _snapshot_assessment_scheme_on_cycle(ctx)
    outcomes = get_eligible_outcomes(ctx)
    aggregates = aggregate_outcomes_to_course_results(ctx, outcomes)
    return upsert_course_term_results(ctx, aggregates)


def _snapshot_assessment_scheme_on_cycle(ctx: dict) -> None:
    default_scheme = ctx.get("assessment_scheme_config")
    active_schemes = ctx.get("active_assessment_scheme_configs") or []
    if not default_scheme and not active_schemes:
        return
    schemes = [scheme for scheme in [default_scheme, *active_schemes] if scheme]
    methods = sorted(set(scheme.get("calculation_method") for scheme in schemes if scheme.get("calculation_method")))
    calculation_method = methods[0] if len(methods) == 1 else "Mixed"
    frappe.db.set_value(
        "Reporting Cycle",
        ctx["name"],
        {
            "assessment_calculation_method": calculation_method,
            "assessment_scheme_snapshot": json.dumps(
                {
                    "default_scheme": default_scheme,
                    "active_scoped_schemes": active_schemes,
                },
                sort_keys=True,
                default=str,
            ),
        },
        update_modified=True,
    )


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
            for fieldname, value in payload.items():
                setattr(course_row, fieldname, value)

        report.save(ignore_permissions=True)
        report_count += 1

    return {"reports": report_count}
