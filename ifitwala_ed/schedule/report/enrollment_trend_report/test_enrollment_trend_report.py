# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/schedule/report/enrollment_trend_report/test_enrollment_trend_report.py

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.schedule.report.enrollment_trend_report import enrollment_trend_report


class TestEnrollmentTrendReport(TestCase):
    @patch("ifitwala_ed.schedule.report.enrollment_trend_report.enrollment_trend_report.frappe.db.sql", return_value=[])
    @patch(
        "ifitwala_ed.schedule.report.enrollment_trend_report.enrollment_trend_report.get_descendant_schools",
        return_value=["SCH-PARENT", "SCH-CHILD"],
    )
    def test_execute_filters_program_enrollment_by_selected_school_and_descendants(
        self,
        _mock_descendants,
        mock_sql,
    ):
        enrollment_trend_report.execute({"school": "SCH-PARENT"})

        query, params = mock_sql.call_args.args[:2]
        self.assertIn("pe.school IN %(school_list)s", query)
        self.assertEqual(params["school_list"], ("SCH-PARENT", "SCH-CHILD"))
