# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/schedule/report/enrollment_report/test_enrollment_report.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.schedule.report.enrollment_report import enrollment_report


class TestEnrollmentReport(TestCase):
    @patch("ifitwala_ed.schedule.report.enrollment_report.enrollment_report.frappe.db.sql", return_value=[])
    @patch(
        "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.get_allowed_schools",
        return_value=["SCH-PARENT", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.frappe.session",
        frappe._dict({"user": "staff@example.com"}),
    )
    def test_get_program_data_uses_descendant_aware_school_scope(
        self,
        mock_get_allowed_schools,
        mock_sql,
    ):
        enrollment_report.get_program_data({"school": "SCH-PARENT"})

        mock_get_allowed_schools.assert_called_once_with("staff@example.com", "SCH-PARENT")
        query, params = mock_sql.call_args.args[:2]
        self.assertIn("pe.school IN %(allowed_schools)s", query)
        self.assertEqual(params["allowed_schools"], ["SCH-PARENT", "SCH-CHILD"])

    @patch("ifitwala_ed.schedule.report.enrollment_report.enrollment_report.frappe.db.sql", return_value=[])
    @patch(
        "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.get_allowed_schools",
        return_value=["SCH-PARENT", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.frappe.session",
        frappe._dict({"user": "staff@example.com"}),
    )
    def test_get_cohort_data_uses_descendant_aware_school_scope(
        self,
        mock_get_allowed_schools,
        mock_sql,
    ):
        enrollment_report.get_cohort_data({"school": "SCH-PARENT", "student_cohort": "COHORT-1"})

        mock_get_allowed_schools.assert_called_once_with("staff@example.com", "SCH-PARENT")
        query, params = mock_sql.call_args.args[:2]
        self.assertIn("pe.school IN %(allowed_schools)s", query)
        self.assertEqual(params["allowed_schools"], ["SCH-PARENT", "SCH-CHILD"])

    @patch("ifitwala_ed.schedule.report.enrollment_report.enrollment_report.frappe.db.sql", return_value=[])
    @patch(
        "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.get_allowed_schools",
        return_value=["SCH-PARENT", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.schedule.report.enrollment_report.enrollment_report.frappe.session",
        frappe._dict({"user": "staff@example.com"}),
    )
    def test_get_course_data_uses_descendant_aware_school_scope(
        self,
        mock_get_allowed_schools,
        mock_sql,
    ):
        enrollment_report.get_course_data({"school": "SCH-PARENT"})

        mock_get_allowed_schools.assert_called_once_with("staff@example.com", "SCH-PARENT")
        query, params = mock_sql.call_args.args[:2]
        self.assertIn("pe.school IN %(allowed_schools)s", query)
        self.assertEqual(params["allowed_schools"], ["SCH-PARENT", "SCH-CHILD"])
