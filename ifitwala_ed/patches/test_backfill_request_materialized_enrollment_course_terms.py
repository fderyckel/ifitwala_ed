from __future__ import annotations

from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.backfill_request_materialized_enrollment_course_terms import (
    _backfill_enrollment_terms,
    execute,
)


class TestBackfillRequestMaterializedEnrollmentCourseTerms(FrappeTestCase):
    def test_execute_backfills_only_target_request_enrollments(self):
        with (
            patch(
                "ifitwala_ed.patches.backfill_request_materialized_enrollment_course_terms.frappe.db.table_exists",
                return_value=True,
            ),
            patch(
                "ifitwala_ed.patches.backfill_request_materialized_enrollment_course_terms.frappe.db.sql",
                return_value=[["PE-0001"], ["PE-0002"]],
            ) as mocked_sql,
            patch(
                "ifitwala_ed.patches.backfill_request_materialized_enrollment_course_terms._backfill_enrollment_terms"
            ) as mocked_backfill,
        ):
            execute()

        self.assertIn("Program Enrollment Course", mocked_sql.call_args.args[0])
        mocked_backfill.assert_any_call("PE-0001")
        mocked_backfill.assert_any_call("PE-0002")

    def test_backfill_enrollment_terms_only_fills_missing_values(self):
        row_missing_both = Mock(course="COURSE-1", term_start="", term_end="")
        row_missing_end = Mock(course="COURSE-2", term_start="TERM-1", term_end="")
        row_complete = Mock(course="COURSE-3", term_start="TERM-1", term_end="TERM-2")
        enrollment = Mock(
            program_offering="PO-0001",
            academic_year="AY-2026",
            school="SCH-0001",
            courses=[row_missing_both, row_missing_end, row_complete],
        )

        with (
            patch(
                "ifitwala_ed.patches.backfill_request_materialized_enrollment_course_terms.frappe.get_doc",
                return_value=enrollment,
            ),
            patch(
                "ifitwala_ed.patches.backfill_request_materialized_enrollment_course_terms._resolve_materialization_course_terms",
                return_value={
                    "COURSE-1": {"term_start": "TERM-1", "term_end": "TERM-2"},
                    "COURSE-2": {"term_start": "TERM-1", "term_end": "TERM-3"},
                    "COURSE-3": {"term_start": "TERM-X", "term_end": "TERM-Y"},
                },
            ) as mocked_resolver,
        ):
            updated_rows = _backfill_enrollment_terms("PE-0001")

        mocked_resolver.assert_called_once_with(
            program_offering="PO-0001",
            academic_year="AY-2026",
            school="SCH-0001",
            courses=["COURSE-1", "COURSE-2"],
        )
        self.assertEqual(updated_rows, 2)
        self.assertEqual(row_missing_both.term_start, "TERM-1")
        self.assertEqual(row_missing_both.term_end, "TERM-2")
        self.assertEqual(row_missing_end.term_start, "TERM-1")
        self.assertEqual(row_missing_end.term_end, "TERM-3")
        self.assertEqual(row_complete.term_start, "TERM-1")
        self.assertEqual(row_complete.term_end, "TERM-2")
        enrollment.save.assert_called_once_with(ignore_permissions=True)
