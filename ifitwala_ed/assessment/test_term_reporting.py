# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import types
from unittest import TestCase
from unittest.mock import Mock, call

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeDoc:
    def __init__(self, name: str | None = None):
        self.name = name
        self.save_calls: list[bool] = []

    def save(self, ignore_permissions=False):
        self.save_calls.append(ignore_permissions)


class _FakeReportDoc(_FakeDoc):
    def __init__(self, name: str | None = None):
        super().__init__(name=name)
        self.courses = []

    def set(self, fieldname, value):
        setattr(self, fieldname, value)

    def append(self, fieldname, _value):
        row = types.SimpleNamespace()
        getattr(self, fieldname).append(row)
        return row


def _term_reporting_extra_modules():
    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.getdate = lambda value: value
    frappe_utils.now_datetime = lambda: "2026-04-17 12:00:00"

    frappe_utils_caching = types.ModuleType("frappe.utils.caching")

    def redis_cache(ttl=None):
        def decorator(fn):
            return fn

        return decorator

    frappe_utils_caching.redis_cache = redis_cache
    return {
        "frappe.utils": frappe_utils,
        "frappe.utils.caching": frappe_utils_caching,
    }


def _patch_single_course_context(module, *, course="COURSE-1", program="PROG-1"):
    module._load_program_enrollments = lambda _ctx: {
        "PE-1": types.SimpleNamespace(
            name="PE-1",
            student="STU-1",
            program=program,
            academic_year="AY-2026",
            school="SCH-1",
        )
    }
    module._load_program_enrollment_courses = lambda _pe_by_name: {
        ("STU-1", course): {
            "program_enrollment": "PE-1",
            "student": "STU-1",
            "course": course,
            "program": program,
            "academic_year": "AY-2026",
            "school": "SCH-1",
        }
    }


class TestTermReporting(TestCase):
    def test_upsert_course_term_results_loads_only_changed_docs(self):
        with stubbed_frappe(extra_modules=_term_reporting_extra_modules()) as frappe:
            existing_rows = [
                types.SimpleNamespace(
                    name="CTR-UNCHANGED",
                    student="STU-1",
                    program_enrollment="PE-1",
                    course="COURSE-1",
                    numeric_score=85.0,
                    grade_value="A",
                    grade_scale="GS-1",
                    task_counted=2,
                    total_weight=2.0,
                    internal_note=None,
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    term="TERM-1",
                    reporting_cycle="RC-1",
                ),
                types.SimpleNamespace(
                    name="CTR-CHANGED",
                    student="STU-2",
                    program_enrollment="PE-2",
                    course="COURSE-2",
                    numeric_score=70.0,
                    grade_value="C",
                    grade_scale="GS-1",
                    task_counted=1,
                    total_weight=1.0,
                    internal_note=None,
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    term="TERM-1",
                    reporting_cycle="RC-1",
                ),
                types.SimpleNamespace(
                    name="CTR-NOOP",
                    student="STU-3",
                    program_enrollment="PE-3",
                    course="COURSE-3",
                    numeric_score=None,
                    grade_value=None,
                    grade_scale=None,
                    task_counted=0,
                    total_weight=0,
                    internal_note="No eligible outcomes",
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    term="TERM-1",
                    reporting_cycle="RC-1",
                ),
                types.SimpleNamespace(
                    name="CTR-RESET",
                    student="STU-4",
                    program_enrollment="PE-4",
                    course="COURSE-4",
                    numeric_score=62.0,
                    grade_value="D",
                    grade_scale="GS-1",
                    task_counted=2,
                    total_weight=2.0,
                    internal_note=None,
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    term="TERM-1",
                    reporting_cycle="RC-1",
                ),
            ]

            def fake_get_all(doctype, filters=None, fields=None, **kwargs):
                if doctype == "Course Term Result":
                    self.assertEqual(filters, {"reporting_cycle": "RC-1"})
                    self.assertIn("term", fields)
                    return existing_rows
                return []

            changed_doc = _FakeDoc(name="CTR-CHANGED")
            reset_doc = _FakeDoc(name="CTR-RESET")
            new_doc = _FakeDoc(name="CTR-NEW")
            frappe.get_all = fake_get_all
            frappe.get_doc = Mock(
                side_effect=lambda doctype, name: {"CTR-CHANGED": changed_doc, "CTR-RESET": reset_doc}[name]
            )
            frappe.new_doc = Mock(return_value=new_doc)

            module = import_fresh("ifitwala_ed.assessment.term_reporting")
            module._grade_label_from_score = lambda grade_scale, numeric_score: "A" if numeric_score == 85.0 else "B"

            aggregates = {
                ("PE-1", "COURSE-1"): module.AggregateRow(
                    student="STU-1",
                    program_enrollment="PE-1",
                    course="COURSE-1",
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    grade_scale="GS-1",
                    numeric_total=170.0,
                    scored_weight=2.0,
                    task_counted=2,
                    note_flags=[],
                    grade_scale_conflict=False,
                ),
                ("PE-2", "COURSE-2"): module.AggregateRow(
                    student="STU-2",
                    program_enrollment="PE-2",
                    course="COURSE-2",
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    grade_scale="GS-1",
                    numeric_total=180.0,
                    scored_weight=2.0,
                    task_counted=2,
                    note_flags=["Late moderation"],
                    grade_scale_conflict=False,
                ),
                ("PE-5", "COURSE-5"): module.AggregateRow(
                    student="STU-5",
                    program_enrollment="PE-5",
                    course="COURSE-5",
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    grade_scale="GS-1",
                    numeric_total=150.0,
                    scored_weight=2.0,
                    task_counted=2,
                    note_flags=[],
                    grade_scale_conflict=False,
                ),
            }

            result = module.upsert_course_term_results(
                {"name": "RC-1", "term": "TERM-1"},
                aggregates,
            )

        self.assertEqual(result, {"updated": 2, "created": 1, "buckets": 3})
        self.assertEqual(
            frappe.get_doc.call_args_list,
            [
                call("Course Term Result", "CTR-CHANGED"),
                call("Course Term Result", "CTR-RESET"),
            ],
        )
        frappe.new_doc.assert_called_once_with("Course Term Result")
        self.assertEqual(changed_doc.save_calls, [True])
        self.assertEqual(reset_doc.save_calls, [True])
        self.assertEqual(new_doc.save_calls, [True])
        self.assertEqual(changed_doc.numeric_score, 90.0)
        self.assertEqual(changed_doc.grade_value, "B")
        self.assertEqual(changed_doc.internal_note, "Late moderation")
        self.assertIsNone(reset_doc.numeric_score)
        self.assertEqual(reset_doc.internal_note, "No eligible outcomes")
        self.assertEqual(new_doc.course, "COURSE-5")
        self.assertEqual(new_doc.grade_value, "B")

    def test_aggregate_outcomes_preloads_criteria_rows_once(self):
        with stubbed_frappe(extra_modules=_term_reporting_extra_modules()) as frappe:
            criteria_fetches: list[dict] = []

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, **kwargs):
                if doctype == "Task Outcome Criterion":
                    criteria_fetches.append(
                        {
                            "filters": filters,
                            "fields": fields,
                            "order_by": order_by,
                        }
                    )
                    return [
                        {"parent": "OUT-1", "assessment_criteria": "CRIT-1", "level_points": 4},
                        {"parent": "OUT-2", "assessment_criteria": "CRIT-2", "level_points": 3},
                    ]
                return []

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.assessment.term_reporting")
            module._load_program_enrollments = lambda _ctx: {
                "PE-1": types.SimpleNamespace(
                    name="PE-1",
                    student="STU-1",
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                )
            }
            module._load_program_enrollment_courses = lambda _pe_by_name: {
                ("STU-1", "COURSE-1"): {
                    "program_enrollment": "PE-1",
                    "student": "STU-1",
                    "course": "COURSE-1",
                    "program": "PROG-1",
                    "academic_year": "AY-2026",
                    "school": "SCH-1",
                }
            }

            aggregates = module.aggregate_outcomes_to_course_results(
                {"school": "SCH-1", "academic_year": "AY-2026"},
                [
                    module.OutcomeRow(
                        name="OUT-1",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-1",
                        grading_mode="Criteria",
                        rubric_scoring_strategy="Separate Criteria",
                        official_score=None,
                        official_grade_value=None,
                        grade_scale="GS-1",
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                    ),
                    module.OutcomeRow(
                        name="OUT-2",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-2",
                        grading_mode="Criteria",
                        rubric_scoring_strategy="Separate Criteria",
                        official_score=None,
                        official_grade_value=None,
                        grade_scale="GS-1",
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                    ),
                ],
            )

        self.assertEqual(len(criteria_fetches), 1)
        self.assertEqual(
            criteria_fetches[0]["filters"],
            {
                "parent": ("in", ["OUT-1", "OUT-2"]),
                "parenttype": "Task Outcome",
                "parentfield": "official_criteria",
            },
        )
        aggregate = aggregates[("PE-1", "COURSE-1")]
        self.assertEqual(aggregate.task_counted, 2)
        self.assertEqual(aggregate.scored_weight, 0.0)
        self.assertEqual(aggregate.note_flags, ["Criteria-only outcome", "Criteria-only outcome"])

    def test_weighted_category_scheme_calculates_component_breakdown(self):
        with stubbed_frappe(extra_modules=_term_reporting_extra_modules()):
            module = import_fresh("ifitwala_ed.assessment.term_reporting")
            _patch_single_course_context(module)

            ctx = {
                "name": "RC-1",
                "school": "SCH-1",
                "academic_year": "AY-2026",
                "term": "TERM-1",
                "assessment_scheme": "ASC-1",
                "assessment_scheme_config": {
                    "name": "ASC-1",
                    "calculation_method": "Weighted Categories",
                    "categories": [
                        {
                            "assessment_category": "Formative",
                            "weight": 40,
                            "active": True,
                            "include_in_term_report": True,
                            "include_in_final_grade": True,
                            "report_label": "Practice",
                            "sort_order": 1,
                        },
                        {
                            "assessment_category": "Summative",
                            "weight": 60,
                            "active": True,
                            "include_in_term_report": True,
                            "include_in_final_grade": True,
                            "report_label": "Evidence",
                            "sort_order": 2,
                        },
                    ],
                },
                "active_assessment_scheme_configs": [],
            }

            aggregates = module.aggregate_outcomes_to_course_results(
                ctx,
                [
                    module.OutcomeRow(
                        name="OUT-1",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-1",
                        grading_mode="Points",
                        rubric_scoring_strategy=None,
                        official_score=80,
                        official_grade_value=None,
                        grade_scale=None,
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                        assessment_category="Formative",
                    ),
                    module.OutcomeRow(
                        name="OUT-2",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-2",
                        grading_mode="Points",
                        rubric_scoring_strategy=None,
                        official_score=90,
                        official_grade_value=None,
                        grade_scale=None,
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                        assessment_category="Summative",
                    ),
                ],
            )

        aggregate = aggregates[("PE-1", "COURSE-1")]
        payload = module._course_term_result_payload(ctx, aggregate)
        self.assertEqual(payload["numeric_score"], 86.0)
        self.assertEqual(payload["total_weight"], 100.0)
        self.assertEqual([component.label for component in aggregate.components], ["Practice", "Evidence"])
        self.assertEqual([component.weight for component in aggregate.components], [40.0, 60.0])

    def test_total_points_scheme_uses_possible_points_as_denominator(self):
        with stubbed_frappe(extra_modules=_term_reporting_extra_modules()):
            module = import_fresh("ifitwala_ed.assessment.term_reporting")
            _patch_single_course_context(module)

            ctx = {
                "name": "RC-1",
                "school": "SCH-1",
                "academic_year": "AY-2026",
                "term": "TERM-1",
                "assessment_scheme": None,
                "assessment_scheme_config": None,
                "active_assessment_scheme_configs": [
                    {
                        "name": "ASC-COURSE-1",
                        "calculation_method": "Total Points",
                        "school": "SCH-1",
                        "academic_year": "AY-2026",
                        "program": "PROG-1",
                        "course": "COURSE-1",
                        "categories": [],
                    }
                ],
            }

            aggregates = module.aggregate_outcomes_to_course_results(
                ctx,
                [
                    module.OutcomeRow(
                        name="OUT-1",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-1",
                        grading_mode="Points",
                        rubric_scoring_strategy=None,
                        official_score=8,
                        official_grade_value=None,
                        grade_scale=None,
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                        max_points=10,
                    ),
                    module.OutcomeRow(
                        name="OUT-2",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-2",
                        grading_mode="Points",
                        rubric_scoring_strategy=None,
                        official_score=45,
                        official_grade_value=None,
                        grade_scale=None,
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                        max_points=50,
                    ),
                ],
            )

        aggregate = aggregates[("PE-1", "COURSE-1")]
        payload = module._course_term_result_payload(ctx, aggregate)
        self.assertEqual(aggregate.assessment_scheme, "ASC-COURSE-1")
        self.assertAlmostEqual(payload["numeric_score"], 88.3333333333)
        self.assertEqual(payload["total_weight"], 60.0)
        self.assertEqual(aggregate.components[0].label, "Total Points")

    def test_weighted_tasks_scheme_uses_delivery_reporting_weight(self):
        with stubbed_frappe(extra_modules=_term_reporting_extra_modules()):
            module = import_fresh("ifitwala_ed.assessment.term_reporting")
            _patch_single_course_context(module)

            ctx = {
                "name": "RC-1",
                "school": "SCH-1",
                "academic_year": "AY-2026",
                "term": "TERM-1",
                "assessment_scheme": "ASC-1",
                "assessment_scheme_config": {
                    "name": "ASC-1",
                    "calculation_method": "Weighted Tasks",
                    "categories": [],
                },
                "active_assessment_scheme_configs": [],
            }

            aggregates = module.aggregate_outcomes_to_course_results(
                ctx,
                [
                    module.OutcomeRow(
                        name="OUT-1",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-1",
                        grading_mode="Points",
                        rubric_scoring_strategy=None,
                        official_score=70,
                        official_grade_value=None,
                        grade_scale=None,
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                        reporting_weight=1,
                    ),
                    module.OutcomeRow(
                        name="OUT-2",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-2",
                        grading_mode="Points",
                        rubric_scoring_strategy=None,
                        official_score=90,
                        official_grade_value=None,
                        grade_scale=None,
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                        reporting_weight=3,
                    ),
                ],
            )

        aggregate = aggregates[("PE-1", "COURSE-1")]
        payload = module._course_term_result_payload(ctx, aggregate)
        self.assertEqual(payload["numeric_score"], 85.0)
        self.assertEqual([component.weight for component in aggregate.components], [1.0, 3.0])
        self.assertEqual([component.component_type for component in aggregate.components], ["Task", "Task"])

    def test_criteria_based_scheme_counts_official_criterion_rows(self):
        with stubbed_frappe(extra_modules=_term_reporting_extra_modules()) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, **kwargs):
                if doctype == "Task Outcome Criterion":
                    return [
                        {"parent": "OUT-1", "assessment_criteria": "CRIT-1", "level_points": 5},
                        {"parent": "OUT-2", "assessment_criteria": "CRIT-1", "level_points": 7},
                        {"parent": "OUT-2", "assessment_criteria": "CRIT-2", "level_points": 4},
                    ]
                return []

            frappe.get_all = fake_get_all
            module = import_fresh("ifitwala_ed.assessment.term_reporting")
            _patch_single_course_context(module)

            ctx = {
                "name": "RC-1",
                "school": "SCH-1",
                "academic_year": "AY-2026",
                "term": "TERM-1",
                "assessment_scheme": "ASC-1",
                "assessment_scheme_config": {
                    "name": "ASC-1",
                    "calculation_method": "Criteria-Based",
                    "categories": [],
                },
                "active_assessment_scheme_configs": [],
            }

            aggregates = module.aggregate_outcomes_to_course_results(
                ctx,
                [
                    module.OutcomeRow(
                        name="OUT-1",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-1",
                        grading_mode="Criteria",
                        rubric_scoring_strategy="Separate Criteria",
                        official_score=None,
                        official_grade_value=None,
                        grade_scale=None,
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                    ),
                    module.OutcomeRow(
                        name="OUT-2",
                        student="STU-1",
                        course="COURSE-1",
                        program="PROG-1",
                        task_delivery="TD-2",
                        grading_mode="Criteria",
                        rubric_scoring_strategy="Sum Total",
                        official_score=None,
                        official_grade_value=None,
                        grade_scale=None,
                        procedural_status=None,
                        due_date=None,
                        lock_date=None,
                    ),
                ],
            )

        aggregate = aggregates[("PE-1", "COURSE-1")]
        payload = module._course_term_result_payload(ctx, aggregate)
        self.assertEqual(payload["numeric_score"], 5.0)
        self.assertEqual([component.component_key for component in aggregate.components], ["CRIT-1", "CRIT-2"])
        self.assertEqual([component.raw_score for component in aggregate.components], [6.0, 4.0])

    def test_generate_student_term_reports_batch_loads_existing_reports_and_skips_unchanged(self):
        with stubbed_frappe(extra_modules=_term_reporting_extra_modules()) as frappe:
            ctr_rows = [
                types.SimpleNamespace(
                    name="CTR-1",
                    student="STU-1",
                    program_enrollment="PE-1",
                    course="COURSE-1",
                    grade_value="A",
                    numeric_score=95.0,
                    override_grade_value=None,
                    teacher_comment="Excellent",
                    is_override=0,
                ),
                types.SimpleNamespace(
                    name="CTR-2",
                    student="STU-2",
                    program_enrollment="PE-2",
                    course="COURSE-2",
                    grade_value="B",
                    numeric_score=82.0,
                    override_grade_value=None,
                    teacher_comment="Solid",
                    is_override=0,
                ),
                types.SimpleNamespace(
                    name="CTR-3",
                    student="STU-3",
                    program_enrollment="PE-3",
                    course="COURSE-3",
                    grade_value="C",
                    numeric_score=71.0,
                    override_grade_value="B",
                    teacher_comment="Improving",
                    is_override=1,
                ),
            ]
            pe_rows = [
                types.SimpleNamespace(
                    name="PE-1", student="STU-1", program="PROG-1", academic_year="AY-2026", school="SCH-1"
                ),
                types.SimpleNamespace(
                    name="PE-2", student="STU-2", program="PROG-1", academic_year="AY-2026", school="SCH-1"
                ),
                types.SimpleNamespace(
                    name="PE-3", student="STU-3", program="PROG-1", academic_year="AY-2026", school="SCH-1"
                ),
            ]
            course_rows = [
                types.SimpleNamespace(name="COURSE-1", course_name="Biology"),
                types.SimpleNamespace(name="COURSE-2", course_name="Chemistry"),
                types.SimpleNamespace(name="COURSE-3", course_name="Physics"),
            ]
            existing_reports = [
                types.SimpleNamespace(
                    name="STR-UNCHANGED",
                    reporting_cycle="RC-1",
                    student="STU-1",
                    program_enrollment="PE-1",
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    term="TERM-1",
                ),
                types.SimpleNamespace(
                    name="STR-CHANGED",
                    reporting_cycle="RC-1",
                    student="STU-2",
                    program_enrollment="PE-2",
                    program="PROG-1",
                    academic_year="AY-2026",
                    school="SCH-1",
                    term="TERM-1",
                ),
            ]
            existing_courses = [
                types.SimpleNamespace(
                    parent="STR-UNCHANGED",
                    course_term_result="CTR-1",
                    course="COURSE-1",
                    course_name="Biology",
                    grade_value="A",
                    numeric_score=95.0,
                    is_override=0,
                    teacher_comment="Excellent",
                ),
                types.SimpleNamespace(
                    parent="STR-CHANGED",
                    course_term_result="CTR-2",
                    course="COURSE-2",
                    course_name="Chemistry",
                    grade_value="C",
                    numeric_score=75.0,
                    is_override=0,
                    teacher_comment="Outdated",
                ),
            ]

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, **kwargs):
                if doctype == "Course Term Result":
                    return ctr_rows
                if doctype == "Program Enrollment":
                    return pe_rows
                if doctype == "Course":
                    return course_rows
                if doctype == "Student Term Report":
                    self.assertEqual(filters["reporting_cycle"], "RC-1")
                    return existing_reports
                if doctype == "Student Term Report Course":
                    return existing_courses
                return []

            changed_report = _FakeReportDoc(name="STR-CHANGED")
            new_report = _FakeReportDoc(name="STR-NEW")
            frappe.get_all = fake_get_all
            frappe.db.get_value = Mock()
            frappe.get_doc = Mock(return_value=changed_report)
            frappe.new_doc = Mock(return_value=new_report)

            module = import_fresh("ifitwala_ed.assessment.term_reporting")
            module.get_cycle_context = lambda reporting_cycle: {
                "name": "RC-1",
                "term": "TERM-1",
            }

            result = module.generate_student_term_reports("RC-1")

        self.assertEqual(result, {"reports": 3})
        self.assertFalse(frappe.db.get_value.called)
        frappe.get_doc.assert_called_once_with("Student Term Report", "STR-CHANGED")
        frappe.new_doc.assert_called_once_with("Student Term Report")
        self.assertEqual(changed_report.save_calls, [True])
        self.assertEqual(new_report.save_calls, [True])
        self.assertEqual(changed_report.reporting_cycle, "RC-1")
        self.assertEqual(changed_report.term, "TERM-1")
        self.assertEqual(len(changed_report.courses), 1)
        self.assertEqual(changed_report.courses[0].course_term_result, "CTR-2")
        self.assertEqual(changed_report.courses[0].grade_value, "B")
        self.assertEqual(new_report.program_enrollment, "PE-3")
        self.assertEqual(new_report.courses[0].grade_value, "B")
        self.assertEqual(new_report.courses[0].is_override, 1)
