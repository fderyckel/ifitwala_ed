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

    def test_get_review_surface_returns_bounded_cycle_result_and_component_payload(self):
        calls: list[dict] = []

        with stubbed_frappe() as frappe:
            frappe.session.user = "academic.admin@example.com"
            frappe.get_roles = lambda user: ["Academic Admin"]
            frappe.db.count = lambda doctype, filters=None: 7

            def fake_get_value(doctype, name, fields=None, as_dict=False):
                self.assertEqual(doctype, "Reporting Cycle")
                self.assertEqual(name, "RC-1")
                return types.SimpleNamespace(
                    name="RC-1",
                    school="SCH-1",
                    academic_year="AY-2026",
                    term="TERM-1",
                    program="PROG-1",
                    assessment_scheme="ASC-1",
                    assessment_calculation_method="Weighted Categories",
                    name_label="Semester 1 Report",
                    task_cutoff_date="2026-04-01",
                    status="Calculated",
                )

            def fake_get_all(doctype, filters=None, fields=None, **kwargs):
                calls.append(
                    {
                        "doctype": doctype,
                        "filters": filters,
                        "fields": fields,
                        "kwargs": kwargs,
                    }
                )
                if doctype == "Reporting Cycle":
                    return [
                        {
                            "name": "RC-1",
                            "school": "SCH-1",
                            "academic_year": "AY-2026",
                            "term": "TERM-1",
                            "program": "PROG-1",
                            "assessment_scheme": "ASC-1",
                            "assessment_calculation_method": "Weighted Categories",
                            "name_label": "Semester 1 Report",
                            "task_cutoff_date": "2026-04-01",
                            "status": "Calculated",
                        }
                    ]
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
                            numeric_score=88.5,
                            grade_value="A",
                            override_grade_value=None,
                            task_counted=4,
                            total_weight=100.0,
                            internal_note="Review complete",
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
                            "weighted_score": 63.0,
                            "grade_value": "A",
                            "evidence_count": 3,
                            "included_outcome_count": 3,
                            "excluded_outcome_count": 0,
                            "calculation_note": None,
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.term_reporting")
            module.get_user_visible_schools = lambda user: ["SCH-1", "SCH-CHILD"]

            payload = module.get_review_surface(course="COURSE-1", limit="25", start="5")

        self.assertEqual(payload["selected_reporting_cycle"], "RC-1")
        self.assertEqual(payload["cycle"]["course_term_results"], 7)
        self.assertEqual(payload["cycle"]["assessment_calculation_method"], "Weighted Categories")
        self.assertEqual(payload["results"]["total_count"], 7)
        self.assertEqual(payload["results"]["page_count"], 1)
        self.assertEqual(payload["results"]["limit"], 25)
        self.assertEqual(payload["results"]["start"], 5)
        self.assertEqual(payload["results"]["rows"][0]["components"][0]["label"], "Summative Evidence")
        self.assertEqual(calls[0]["doctype"], "Reporting Cycle")
        self.assertEqual(calls[0]["filters"], {"school": ["in", ["SCH-1", "SCH-CHILD"]]})
        self.assertEqual(calls[1]["doctype"], "Course Term Result")
        self.assertEqual(calls[1]["filters"], {"reporting_cycle": "RC-1", "course": "COURSE-1"})
        self.assertEqual(calls[1]["kwargs"]["limit"], 25)
        self.assertEqual(calls[1]["kwargs"]["limit_start"], 5)

    def test_get_review_surface_rejects_unscoped_reporting_cycle(self):
        with stubbed_frappe() as frappe:
            frappe.session.user = "instructor@example.com"
            frappe.get_roles = lambda user: ["Instructor"]
            frappe.get_all = lambda *args, **kwargs: []
            frappe.db.get_value = lambda *args, **kwargs: types.SimpleNamespace(
                name="RC-2",
                school="SCH-2",
                academic_year="AY-2026",
                term="TERM-1",
                program=None,
                assessment_scheme=None,
                assessment_calculation_method=None,
                name_label="Other School Report",
                task_cutoff_date=None,
                status="Calculated",
            )

            module = import_fresh("ifitwala_ed.api.term_reporting")
            module.get_user_visible_schools = lambda user: ["SCH-1"]

            with self.assertRaises(frappe.PermissionError):
                module.get_review_surface(reporting_cycle="RC-2")

    def test_get_review_surface_requires_term_reporting_review_role(self):
        with stubbed_frappe() as frappe:
            frappe.session.user = "student@example.com"
            frappe.get_roles = lambda user: ["Student"]

            module = import_fresh("ifitwala_ed.api.term_reporting")
            module.get_user_visible_schools = lambda user: ["SCH-1"]

            with self.assertRaises(frappe.PermissionError):
                module.get_review_surface()
