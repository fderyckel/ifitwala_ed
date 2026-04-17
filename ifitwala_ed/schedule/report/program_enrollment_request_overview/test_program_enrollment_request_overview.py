from unittest import TestCase
from unittest.mock import call, patch

import frappe

from ifitwala_ed.schedule.report.program_enrollment_request_overview import (
    program_enrollment_request_overview as report,
)


class TestProgramEnrollmentRequestOverview(TestCase):
    @patch(
        "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview.get_allowed_schools",
        return_value=["SCH-PARENT", "SCH-CHILD"],
    )
    @patch(
        "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview.frappe.session",
        frappe._dict({"user": "staff@example.com"}),
    )
    @patch(
        "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview.frappe.db.sql",
        return_value=[],
    )
    def test_execute_uses_descendant_aware_school_scope(self, mock_sql, mock_allowed_schools):
        report.execute(
            {
                "view_mode": report.VIEW_MODE_SUMMARY,
                "school": "SCH-PARENT",
                "academic_year": "AY-2026",
                "request_kind": "Academic",
            }
        )

        mock_allowed_schools.assert_called_once_with("staff@example.com", "SCH-PARENT")
        query, params = mock_sql.call_args.args[:2]
        self.assertIn("per.school IN %(allowed_schools)s", query)
        self.assertEqual(params["allowed_schools"], ("SCH-PARENT", "SCH-CHILD"))

    def test_matrix_requires_program_offering(self):
        with self.assertRaises(frappe.ValidationError):
            report.execute({"view_mode": report.VIEW_MODE_MATRIX, "school": "SCH-1", "academic_year": "AY-2026"})

    def test_window_tracker_requires_selection_window(self):
        with self.assertRaises(frappe.ValidationError):
            report.execute(
                {
                    "view_mode": report.VIEW_MODE_WINDOW_TRACKER,
                    "school": "SCH-1",
                    "academic_year": "AY-2026",
                }
            )

    def test_dedupe_keeps_latest_request_per_student_context(self):
        rows = [
            {
                "name": "PER-0002",
                "student": "STU-1",
                "program_offering": "PO-1",
                "academic_year": "AY-2026",
                "request_kind": "Academic",
            },
            {
                "name": "PER-0001",
                "student": "STU-1",
                "program_offering": "PO-1",
                "academic_year": "AY-2026",
                "request_kind": "Academic",
            },
        ]

        deduped = report._dedupe_request_rows(rows, latest_only=True)

        self.assertEqual([row["name"] for row in deduped], ["PER-0002"])

    def test_extract_invalid_reason_info_maps_buckets(self):
        row = {
            "validation_status": "Invalid",
            "validation_payload": """
            {
                "results": {
                    "basket": {
                        "violations": [
                            {"code": "require_group_coverage", "message": "Basket must include at least one course from group 'Group 3'."}
                        ]
                    },
                    "courses": [
                        {"course": "BIO", "reasons": ["Capacity full for this course."]},
                        {"course": "MATH", "reasons": ["Prerequisite requirements not met."]}
                    ]
                }
            }
            """,
        }

        info = report._extract_invalid_reason_info(row)

        self.assertEqual(
            info["buckets"],
            ["Basket Group Coverage", "Capacity Full", "Prerequisite"],
        )
        self.assertIn("No places are currently available in BIO.", info["detail"])

    def test_build_summary_view_keeps_zero_count_offered_courses(self):
        requests = [
            {
                "name": "PER-0001",
                "validation_status": "Valid",
                "request_status": "Approved",
                "requires_override": 0,
                "invalid_reason_buckets": [],
                "courses": [{"course": "BIO", "course_name": "Biology", "required": 0}],
            }
        ]
        course_catalog = [
            {"course": "BIO", "course_name": "Biology", "required": 0, "fieldname": "course_001_bio"},
            {"course": "CHEM", "course_name": "Chemistry", "required": 1, "fieldname": "course_002_chem"},
        ]

        _columns, data = report._build_summary_view(requests, course_catalog)

        self.assertEqual(data[0]["course"], "BIO")
        self.assertEqual(data[0]["students_requested"], 1)
        self.assertEqual(data[1]["course"], "CHEM")
        self.assertEqual(data[1]["students_requested"], 0)

    @patch(
        "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview._get_live_choice_states",
        return_value={
            "PER-0001": {
                "ready_for_submit": False,
                "reasons": ["Choose at least one course in Language Group."],
            }
        },
    )
    def test_build_window_tracker_view_surfaces_missing_and_problem_rows(self, _mock_live_choice_states):
        window_rows = [
            {
                "student": "STU-2",
                "student_name": "Ben Student",
                "program_enrollment_request": "",
            },
            {
                "student": "STU-1",
                "student_name": "Ada Student",
                "program_enrollment_request": "PER-0001",
            },
            {
                "student": "STU-3",
                "student_name": "Cara Student",
                "program_enrollment_request": "PER-0003",
            },
        ]
        requests = [
            {
                "name": "PER-0001",
                "request_kind": "Academic",
                "request_status": "Draft",
                "validation_status": "Not Validated",
                "requires_override": 0,
                "override_approved": 0,
                "invalid_reason_buckets": [],
                "submitted_on": None,
                "invalid_reason_detail": "",
            },
            {
                "name": "PER-0003",
                "request_kind": "Academic",
                "request_status": "Approved",
                "validation_status": "Invalid",
                "requires_override": 1,
                "override_approved": 0,
                "invalid_reason_buckets": ["Prerequisite"],
                "submitted_on": "2026-03-28 11:00:00",
                "invalid_reason_detail": "Prerequisite review required.",
                "override_reason": "",
            },
        ]

        _columns, data = report._build_window_tracker_view(
            window_rows, requests, frappe._dict({"request_kind": "Academic"})
        )

        by_student = {row["student"]: row for row in data}
        self.assertEqual(by_student["STU-1"]["submission_status"], report.SUBMISSION_STATUS_NOT_SUBMITTED)
        self.assertEqual(by_student["STU-1"]["current_state"], report.CURRENT_STATE_BLOCKED)
        self.assertEqual(by_student["STU-1"]["problem_status"], report.PROBLEM_STATUS_SELECTION_BLOCKED)
        self.assertIn("Language Group", by_student["STU-1"]["problem_detail"])

        self.assertEqual(by_student["STU-2"]["submission_status"], report.SUBMISSION_STATUS_MISSING_REQUEST)
        self.assertEqual(by_student["STU-2"]["problem_status"], report.PROBLEM_STATUS_MISSING_REQUEST)

        self.assertEqual(by_student["STU-3"]["submission_status"], report.SUBMISSION_STATUS_SUBMITTED)
        self.assertEqual(by_student["STU-3"]["problem_status"], report.PROBLEM_STATUS_NEEDS_OVERRIDE)

    def test_get_live_choice_states_uses_loaded_request_models_and_caches_offering_semantics(self):
        requests = [
            {
                "name": "PER-0001",
                "student": "STU-1",
                "program_offering": "PO-1",
                "program": "PROG-1",
                "academic_year": "AY-2026",
                "request_kind": "Academic",
                "request_status": "Draft",
                "validation_status": "Not Validated",
                "submitted_on": None,
                "courses": [
                    {
                        "course": "BIO",
                        "required": 0,
                        "applied_basket_group": "Language Group",
                        "choice_rank": 1,
                    }
                ],
            },
            {
                "name": "PER-0002",
                "student": "STU-2",
                "program_offering": "PO-1",
                "program": "PROG-1",
                "academic_year": "AY-2026",
                "request_kind": "Academic",
                "request_status": "Draft",
                "validation_status": "Not Validated",
                "submitted_on": None,
                "courses": [
                    {
                        "course": "CHEM",
                        "required": 0,
                        "applied_basket_group": "",
                        "choice_rank": 2,
                    }
                ],
            },
            {
                "name": "PER-0003",
                "student": "STU-3",
                "program_offering": "PO-2",
                "program": "PROG-2",
                "academic_year": "AY-2026",
                "request_kind": "Academic",
                "request_status": "Approved",
                "validation_status": "Valid",
                "submitted_on": "2026-03-28 11:00:00",
                "courses": [],
            },
        ]
        offering_semantics = {"BIO": {"course_name": "Biology"}, "CHEM": {"course_name": "Chemistry"}}

        def fake_choice_state(request_doc, *, can_edit, offering_semantics=None, required_basket_groups=None):
            self.assertFalse(can_edit)
            self.assertEqual(request_doc.status, "Draft")
            self.assertTrue(request_doc.courses)
            self.assertIsInstance(request_doc.courses[0], frappe._dict)
            self.assertEqual(
                offering_semantics, {"BIO": {"course_name": "Biology"}, "CHEM": {"course_name": "Chemistry"}}
            )
            self.assertIsNone(required_basket_groups)
            return {
                "summary": {"ready_for_submit": request_doc.name == "PER-0002"},
                "validation": {
                    "reasons": [] if request_doc.name == "PER-0002" else ["Choose at least one course in Group A."]
                },
            }

        with (
            patch(
                "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview.get_offering_course_semantics",
                return_value=offering_semantics,
            ) as semantics_mock,
            patch(
                "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview.get_program_enrollment_request_choice_state",
                side_effect=fake_choice_state,
            ) as choice_state_mock,
            patch(
                "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview.frappe.get_doc"
            ) as get_doc_mock,
        ):
            live_states = report._get_live_choice_states(requests)

        semantics_mock.assert_called_once_with("PO-1")
        self.assertEqual(
            choice_state_mock.call_args_list,
            [
                call(
                    report._choice_state_request_doc(requests[0]),
                    can_edit=False,
                    offering_semantics=offering_semantics,
                ),
                call(
                    report._choice_state_request_doc(requests[1]),
                    can_edit=False,
                    offering_semantics=offering_semantics,
                ),
            ],
        )
        self.assertFalse(get_doc_mock.called)
        self.assertEqual(
            live_states,
            {
                "PER-0001": {
                    "ready_for_submit": False,
                    "reasons": ["Choose at least one course in Group A."],
                },
                "PER-0002": {
                    "ready_for_submit": True,
                    "reasons": [],
                },
            },
        )

    @patch(
        "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview.frappe.db.sql",
        return_value=[],
    )
    def test_fetch_request_rows_can_scope_to_selection_window(self, mock_sql):
        report._fetch_request_rows(
            frappe._dict(
                {
                    "school": "SCH-1",
                    "academic_year": "AY-2026",
                    "program": "",
                    "program_offering": "",
                    "selection_window": "SEW-0001",
                    "request_kind": "Academic",
                }
            ),
            ["SCH-1"],
        )

        query, params = mock_sql.call_args.args[:2]
        self.assertIn("per.selection_window = %(selection_window)s", query)
        self.assertEqual(params["selection_window"], "SEW-0001")
