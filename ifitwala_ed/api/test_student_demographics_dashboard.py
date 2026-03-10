# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/test_student_demographics_dashboard.py

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.student_demographics_dashboard import get_dashboard, get_slice_entities


class TestStudentDemographicsDashboard(FrappeTestCase):
    def test_dashboard_includes_student_house_by_cohort(self):
        students = [
            {
                "name": "STU-001",
                "student_full_name": "Ada One",
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
            },
            {
                "name": "STU-002",
                "student_full_name": "Ben Two",
                "anchor_school": "School A",
                "cohort": "Cohort A",
                "student_house": "Blue House",
                "student_gender": "Male",
                "student_nationality": "TH",
                "student_second_nationality": "",
                "student_first_language": "English",
                "student_second_language": "",
                "residency_status": "Expat Resident",
                "student_date_of_birth": "2013-06-15",
            },
            {
                "name": "STU-003",
                "student_full_name": "Cam Three",
                "anchor_school": "School A",
                "cohort": "Cohort B",
                "student_house": "Red House",
                "student_gender": "Other",
                "student_nationality": "FR",
                "student_second_nationality": "",
                "student_first_language": "French",
                "student_second_language": "",
                "residency_status": "Boarder",
                "student_date_of_birth": "2012-09-30",
            },
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
        self.assertEqual(len(house_rows), 2)

        cohort_a = next(row for row in house_rows if row.get("cohort") == "Cohort A")
        self.assertEqual(
            cohort_a.get("buckets"),
            [
                {
                    "label": "Blue House",
                    "count": 1,
                    "sliceKey": "student:student_house:Blue House:cohort:Cohort A",
                },
                {
                    "label": "Red House",
                    "count": 1,
                    "sliceKey": "student:student_house:Red House:cohort:Cohort A",
                },
            ],
        )
        self.assertEqual(
            (payload.get("slices") or {}).get("student:student_house:Red House:cohort:Cohort B", {}).get("title"),
            "Cohort B · Red House",
        )

    def test_student_house_slice_returns_matching_students(self):
        students = [
            {
                "name": "STU-001",
                "student_full_name": "Ada One",
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
            },
            {
                "name": "STU-002",
                "student_full_name": "Ben Two",
                "anchor_school": "School A",
                "cohort": "Cohort A",
                "student_house": "Blue House",
                "student_gender": "Male",
                "student_nationality": "TH",
                "student_second_nationality": "",
                "student_first_language": "English",
                "student_second_language": "",
                "residency_status": "Expat Resident",
                "student_date_of_birth": "2013-06-15",
            },
        ]

        with (
            patch(
                "ifitwala_ed.api.student_demographics_dashboard._get_demographics_access_context",
                return_value={"user": "analytics@example.com", "mode": "full"},
            ),
            patch("ifitwala_ed.api.student_demographics_dashboard._get_active_students", return_value=students),
            patch("ifitwala_ed.api.student_demographics_dashboard._get_guardian_links", return_value=[]),
        ):
            rows = get_slice_entities(
                slice_key="student:student_house:Red House:cohort:Cohort A",
                filters={"school": "School A"},
            )

        self.assertEqual(
            rows,
            [
                {
                    "id": "STU-001",
                    "name": "Ada One",
                    "cohort": "Cohort A",
                    "subtitle": "Cohort A · Red House",
                    "nationality": "TH",
                }
            ],
        )
