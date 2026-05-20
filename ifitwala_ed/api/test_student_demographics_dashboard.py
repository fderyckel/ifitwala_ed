# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/test_student_demographics_dashboard.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import student_demographics_dashboard as demographics_dashboard
from ifitwala_ed.api.student_demographics_dashboard import get_dashboard, get_slice_entities


class TestStudentDemographicsDashboard(FrappeTestCase):
    def make_student(self, index: int, **overrides):
        student = {
            "name": f"STU-{index:03d}",
            "student_full_name": f"Student {index}",
            "anchor_school": "School A",
            "cohort": "Cohort A",
            "student_house": "Red House",
            "student_gender": "Female",
            "student_nationality": "TH",
            "student_second_nationality": "",
            "student_first_language": "English",
            "student_second_language": "",
            "residency_status": "Local Resident",
            "student_date_of_birth": "2014-01-01",
        }
        student.update(overrides)
        return student

    def assert_no_slice_metadata(self, payload):
        if isinstance(payload, dict):
            self.assertNotIn("sliceKey", payload)
            self.assertNotIn("sliceKeys", payload)
            self.assertNotIn("slices", payload)
            for value in payload.values():
                self.assert_no_slice_metadata(value)
        elif isinstance(payload, list):
            for value in payload:
                self.assert_no_slice_metadata(value)

    def test_active_students_intersects_requested_school_with_authorized_scope(self):
        with (
            patch(
                "ifitwala_ed.api.student_demographics_dashboard.get_descendant_schools",
                return_value=["SCH-ROOT", "SCH-CHILD", "SCH-SIBLING"],
            ),
            patch("ifitwala_ed.api.student_demographics_dashboard.frappe.db.sql", return_value=[]) as sql,
        ):
            demographics_dashboard._get_active_students(
                {"school": "SCH-ROOT"},
                {"user": "assistant@example.com", "mode": "full", "school_scope": ["SCH-CHILD"]},
            )

        query, params = sql.call_args.args[:2]
        self.assertIn("st.anchor_school in %(schools)s", query)
        self.assertNotIn("st.student_full_name", query)
        self.assertEqual(params["schools"], ("SCH-CHILD",))

    def test_active_students_uses_instructor_scope_condition_before_aggregation(self):
        with (
            patch(
                "ifitwala_ed.api.student_demographics_dashboard.get_instructor_student_scope_condition",
                return_value="EXISTS (SELECT 1 FROM instructor_scope)",
            ) as instructor_scope,
            patch("ifitwala_ed.api.student_demographics_dashboard.frappe.db.sql", return_value=[]) as sql,
        ):
            demographics_dashboard._get_active_students(
                {},
                {"user": "teacher@example.com", "mode": "instructor"},
            )

        query = sql.call_args.args[0]
        instructor_scope.assert_called_once_with("teacher@example.com", table_alias="st")
        self.assertIn("EXISTS (SELECT 1 FROM instructor_scope)", query)

    def test_dashboard_suppresses_low_count_demographic_buckets(self):
        students = [self.make_student(index) for index in range(1, 6)]
        students.append(
            self.make_student(
                6,
                student_full_name="Ben Hidden",
                student_house="Blue House",
                student_gender="Male",
                student_nationality="FR",
                student_first_language="French",
                residency_status="Expat Resident",
                student_date_of_birth="2013-06-15",
            )
        )

        with (
            patch(
                "ifitwala_ed.api.student_demographics_dashboard._get_demographics_access_context",
                return_value={"user": "analytics@example.com", "mode": "full"},
            ),
            patch("ifitwala_ed.api.student_demographics_dashboard._get_active_students", return_value=students),
            patch("ifitwala_ed.api.student_demographics_dashboard._get_guardian_links", return_value=[]),
        ):
            payload = get_dashboard(filters={"school": "School A"})

        house_rows = payload.get("student_house_by_cohort") or []
        self.assertEqual(len(house_rows), 1)

        cohort_a = next(row for row in house_rows if row.get("cohort") == "Cohort A")
        self.assertEqual(
            cohort_a.get("buckets"),
            [
                {
                    "label": "Red House",
                    "count": 5,
                },
            ],
        )
        self.assertEqual(payload["gender_by_cohort"][0]["female"], 5)
        self.assertEqual(payload["gender_by_cohort"][0]["male"], 0)
        self.assert_no_slice_metadata(payload)
        payload_text = repr(payload)
        self.assertNotIn("Blue House", payload_text)
        self.assertNotIn("FR", payload_text)
        self.assertNotIn("STU-006", payload_text)
        self.assertNotIn("Ben Hidden", payload_text)

    def test_dashboard_rolls_up_combined_suppressed_demographic_buckets(self):
        houses = ["Blue House", "Green House", "Yellow House", "Purple House", "Orange House"]
        students = [
            self.make_student(
                index,
                student_house=house,
                student_nationality=f"Nationality {index}",
                student_first_language=f"Language {index}",
            )
            for index, house in enumerate(houses, start=1)
        ]

        with (
            patch(
                "ifitwala_ed.api.student_demographics_dashboard._get_demographics_access_context",
                return_value={"user": "analytics@example.com", "mode": "full"},
            ),
            patch("ifitwala_ed.api.student_demographics_dashboard._get_active_students", return_value=students),
            patch("ifitwala_ed.api.student_demographics_dashboard._get_guardian_links", return_value=[]),
        ):
            payload = get_dashboard(filters={"school": "School A"})

        house_rows = payload.get("student_house_by_cohort") or []
        self.assertEqual(len(house_rows), 1)
        self.assertEqual(
            house_rows[0].get("buckets"),
            [{"label": demographics_dashboard.SUPPRESSED_BUCKET_LABEL, "count": 5}],
        )
        self.assert_no_slice_metadata(payload)
        payload_text = repr(payload)
        for house in houses:
            self.assertNotIn(house, payload_text)

    def test_slice_entities_is_disabled_for_aggregate_only_privacy(self):
        with self.assertRaises(frappe.PermissionError):
            get_slice_entities(
                slice_key="student:student_house:Red House:cohort:Cohort A",
                filters={"school": "School A"},
            )
