from unittest import TestCase

from ifitwala_ed.schedule.report.enrollment_intent_course_analytics import (
    enrollment_intent_course_analytics as report,
)


class TestEnrollmentIntentCourseAnalytics(TestCase):
    def test_course_rows_count_only_students_intending_to_enroll(self):
        requests = [
            {
                "name": "PER-1",
                "student": "STU-1",
                "program_offering": "PO-1",
                "request_status": "Submitted",
                "validation_status": "Valid",
                "requires_override": 0,
                "enrollment_intent": "Intends to Enroll",
                "collect_enrollment_intent": 1,
                "courses": [{"course": "BIO", "course_name": "Biology", "required": 0}],
            },
            {
                "name": "PER-2",
                "student": "STU-2",
                "program_offering": "PO-1",
                "request_status": "Submitted",
                "validation_status": "Not Validated",
                "requires_override": 0,
                "enrollment_intent": "Does Not Intend to Enroll",
                "collect_enrollment_intent": 1,
                "courses": [{"course": "BIO", "course_name": "Biology", "required": 0}],
            },
        ]

        rows = report._build_course_rows(requests, materialized_requests={"PER-1"})

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["course"], "BIO")
        self.assertEqual(rows[0]["intent_students"], 1)
        self.assertEqual(rows[0]["valid"], 1)
        self.assertEqual(rows[0]["materialized"], 1)
