# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/students/report/attendance_report/test_attendance_report.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.students.report.attendance_report import attendance_report


class TestAttendanceReport(TestCase):
    @patch("ifitwala_ed.students.report.attendance_report.attendance_report.frappe.db.sql", return_value=[])
    @patch("ifitwala_ed.students.report.attendance_report.attendance_report.frappe.get_all")
    @patch(
        "ifitwala_ed.students.report.attendance_report.attendance_report.get_descendant_schools",
        return_value=["SCH-PARENT", "SCH-CHILD"],
    )
    def test_execute_filters_attendance_by_selected_school_and_descendants(
        self,
        _mock_descendants,
        mock_get_all,
        mock_sql,
    ):
        mock_get_all.return_value = [
            frappe._dict(
                {
                    "name": "PRESENT",
                    "attendance_code": "P",
                    "count_as_present": 1,
                    "display_order": 1,
                }
            )
        ]

        attendance_report.execute(
            {
                "school": "SCH-PARENT",
                "academic_year": "AY-2026",
                "from_date": "2026-01-01",
                "to_date": "2026-01-31",
                "whole_day": 1,
            }
        )

        query, params = mock_sql.call_args.args[:2]
        self.assertIn("sa.school IN %(school_list)s", query)
        self.assertEqual(params["school_list"], ("SCH-PARENT", "SCH-CHILD"))
