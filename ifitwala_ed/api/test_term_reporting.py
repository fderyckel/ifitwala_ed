# ifitwala_ed/api/test_term_reporting.py

from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestTermReportingApi(TestCase):
    def test_get_course_term_results_returns_scheme_and_components(self):
        calls: list[dict] = []

        with stubbed_frappe() as frappe:

            def fake_get_all(doctype, filters=None, fields=None, **kwargs):
                calls.append(
                    {
                        "doctype": doctype,
                        "filters": filters,
                        "fields": fields,
                        "kwargs": kwargs,
                    }
                )
                if doctype == "Course Term Result":
                    return [
                        types.SimpleNamespace(
                            name="CTR-1",
                            student="STU-1",
                            program_enrollment="PE-1",
                            course="COURSE-1",
                            program="PROG-1",
                            academic_year="AY-2026",
                            term="TERM-1",
                            assessment_scheme="ASC-1",
                            assessment_calculation_method="Weighted Categories",
                            grade_scale="GS-1",
                            numeric_score=86.0,
                            grade_value="B",
                            override_grade_value=None,
                            task_counted=2,
                            total_weight=100.0,
                            internal_note=None,
                        )
                    ]
                if doctype == "Course Term Result Component":
                    return [
                        {
                            "parent": "CTR-1",
                            "component_type": "Category",
                            "component_key": "Summative",
                            "label": "Summative Evidence",
                            "assessment_category": "Summative",
                            "assessment_criteria": None,
                            "weight": 70.0,
                            "raw_score": 90.0,
                            "weighted_score": 6300.0,
                            "grade_value": "A",
                            "evidence_count": 1,
                            "included_outcome_count": 1,
                            "excluded_outcome_count": 0,
                            "calculation_note": None,
                        }
                    ]
                return []

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.term_reporting")
            payload = module.get_course_term_results("RC-1", course="COURSE-1", limit="25", start="5")

        self.assertEqual(payload["count"], 1)
        row = payload["rows"][0]
        self.assertEqual(row["assessment_scheme"], "ASC-1")
        self.assertEqual(row["assessment_calculation_method"], "Weighted Categories")
        self.assertEqual(row["grade_scale"], "GS-1")
        self.assertEqual(
            row["components"],
            [
                {
                    "component_type": "Category",
                    "component_key": "Summative",
                    "label": "Summative Evidence",
                    "assessment_category": "Summative",
                    "assessment_criteria": None,
                    "weight": 70.0,
                    "raw_score": 90.0,
                    "weighted_score": 6300.0,
                    "grade_value": "A",
                    "evidence_count": 1,
                    "included_outcome_count": 1,
                    "excluded_outcome_count": 0,
                    "calculation_note": None,
                }
            ],
        )
        self.assertEqual(calls[0]["filters"], {"reporting_cycle": "RC-1", "course": "COURSE-1"})
        self.assertEqual(calls[0]["kwargs"]["limit"], 25)
        self.assertEqual(calls[0]["kwargs"]["limit_start"], 5)
        self.assertEqual(calls[1]["doctype"], "Course Term Result Component")
        self.assertEqual(calls[1]["filters"]["parent"], ("in", ["CTR-1"]))
        self.assertEqual(calls[1]["kwargs"]["limit"], 0)
