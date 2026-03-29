# Copyright (c) 2024, fdR and Contributors
# See license.txt

# ifitwala_ed/schedule/doctype/student_group/test_student_group.py

from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.schedule.doctype.student_group.student_group import (
    StudentGroup,
    build_in_clause_placeholders,
    descendants_inclusive,
    get_single_offering_academic_year,
    instructor_log_sync_context,
    is_same_or_descendant,
)
from ifitwala_ed.schedule.student_group_scheduling import fetch_block_grid


class TestStudentGroup(TestCase):
    def test_build_in_clause_placeholders_matches_length(self):
        self.assertEqual(build_in_clause_placeholders(["A", "B", "C"]), "%s, %s, %s")

    def test_descendants_inclusive_returns_empty_without_school(self):
        self.assertEqual(descendants_inclusive(""), set())

    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.get_school_lftrgt")
    def test_is_same_or_descendant_respects_nestedset_bounds(self, mock_lftrgt):
        def _bounds(school):
            mapping = {
                "ROOT": (1, 10),
                "CHILD": (2, 3),
                "SIBLING": (11, 12),
            }
            return mapping.get(school, (None, None))

        mock_lftrgt.side_effect = _bounds

        self.assertTrue(is_same_or_descendant("ROOT", "CHILD"))
        self.assertFalse(is_same_or_descendant("ROOT", "SIBLING"))

    def test_instructor_log_sync_context_detects_designation_changes(self):
        previous = type(
            "Doc",
            (),
            {
                "school": "Ifitwala Secondary School",
                "program_offering": "IB DP Class of 2027",
                "program": "Diploma Program",
                "academic_year": "IIS 2025-2026",
                "term": "",
                "course": "",
                "instructors": [type("Row", (), {"instructor": "Cedric Villani", "designation": "Teacher"})()],
            },
        )()
        current = type(
            "Doc",
            (),
            {
                "school": "Ifitwala Secondary School",
                "program_offering": "IB DP Class of 2027",
                "program": "Diploma Program",
                "academic_year": "IIS 2025-2026",
                "term": "",
                "course": "",
                "instructors": [type("Row", (), {"instructor": "Cedric Villani", "designation": "Advisor"})()],
            },
        )()

        should_sync, targets = instructor_log_sync_context(previous, current)

        self.assertTrue(should_sync)
        self.assertEqual(targets, {"Cedric Villani"})

    def test_instructor_log_sync_context_includes_removed_instructors(self):
        previous = type(
            "Doc",
            (),
            {
                "school": "Ifitwala Secondary School",
                "program_offering": "IB DP Class of 2027",
                "program": "Diploma Program",
                "academic_year": "IIS 2025-2026",
                "term": "",
                "course": "",
                "instructors": [type("Row", (), {"instructor": "Cedric Villani", "designation": "Teacher"})()],
            },
        )()
        current = type(
            "Doc",
            (),
            {
                "school": "Ifitwala Secondary School",
                "program_offering": "IB DP Class of 2027",
                "program": "Diploma Program",
                "academic_year": "IIS 2025-2026",
                "term": "",
                "course": "",
                "instructors": [],
            },
        )()

        should_sync, targets = instructor_log_sync_context(previous, current)

        self.assertTrue(should_sync)
        self.assertEqual(targets, {"Cedric Villani"})

    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.frappe.get_all")
    def test_get_single_offering_academic_year_returns_value_for_exactly_one_ay(self, mock_get_all):
        mock_get_all.return_value = [{"academic_year": "AY-2026"}]

        result = get_single_offering_academic_year("PO-1")

        self.assertEqual(result, {"academic_year": "AY-2026"})

    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.frappe.get_all")
    def test_get_single_offering_academic_year_returns_none_for_multiple_ays(self, mock_get_all):
        mock_get_all.return_value = [{"academic_year": "AY-2026"}, {"academic_year": "AY-2027"}]

        result = get_single_offering_academic_year("PO-1")

        self.assertEqual(result, {"academic_year": None})


class TestStudentGroupScheduleAdvisories(FrappeTestCase):
    def test_validate_schedule_rows_warns_for_break_block(self):
        group = frappe.get_doc(
            {
                "doctype": "Student Group",
                "group_based_on": "Course",
                "instructors": [
                    {
                        "instructor": "Instructor One",
                    }
                ],
                "student_group_schedule": [
                    {
                        "rotation_day": 1,
                        "block_number": 2,
                        "instructor": "Instructor One",
                    }
                ],
            }
        )
        schedule = frappe._dict(
            {
                "name": "Schedule-1",
                "rotation_days": 3,
                "school_schedule_block": [
                    frappe._dict(
                        {
                            "rotation_day": 1,
                            "block_number": 2,
                            "from_time": "10:00:00",
                            "to_time": "10:30:00",
                            "block_type": "Other",
                            "description": "Lunch Break",
                        }
                    )
                ],
            }
        )

        with (
            patch.object(StudentGroup, "_get_school_schedule", return_value=schedule),
            patch("frappe.msgprint") as msgprint,
        ):
            group._validate_schedule_rows()

        self.assertEqual(str(group.student_group_schedule[0].from_time), "10:00:00")
        self.assertEqual(str(group.student_group_schedule[0].to_time), "10:30:00")
        msgprint.assert_called_once()
        self.assertIn("Lunch Break", msgprint.call_args.args[0])
        self.assertEqual(msgprint.call_args.kwargs.get("indicator"), "orange")

    def test_validate_schedule_rows_skips_warning_for_matching_course_block(self):
        group = frappe.get_doc(
            {
                "doctype": "Student Group",
                "group_based_on": "Course",
                "instructors": [
                    {
                        "instructor": "Instructor One",
                    }
                ],
                "student_group_schedule": [
                    {
                        "rotation_day": 1,
                        "block_number": 1,
                        "instructor": "Instructor One",
                    }
                ],
            }
        )
        schedule = frappe._dict(
            {
                "name": "Schedule-1",
                "rotation_days": 3,
                "school_schedule_block": [
                    frappe._dict(
                        {
                            "rotation_day": 1,
                            "block_number": 1,
                            "from_time": "08:00:00",
                            "to_time": "08:45:00",
                            "block_type": "Course",
                            "description": "",
                        }
                    )
                ],
            }
        )

        with (
            patch.object(StudentGroup, "_get_school_schedule", return_value=schedule),
            patch("frappe.msgprint") as msgprint,
        ):
            group._validate_schedule_rows()

        msgprint.assert_not_called()

    def test_fetch_block_grid_includes_block_warning_metadata(self):
        schedule = frappe._dict(
            {
                "school_schedule_block": [
                    frappe._dict(
                        {
                            "rotation_day": 1,
                            "block_number": 1,
                            "from_time": "08:00:00",
                            "to_time": "08:45:00",
                            "block_type": "Course",
                            "description": "",
                        }
                    ),
                    frappe._dict(
                        {
                            "rotation_day": 1,
                            "block_number": 2,
                            "from_time": "10:00:00",
                            "to_time": "10:30:00",
                            "block_type": "Other",
                            "description": "Lunch Break",
                        }
                    ),
                ]
            }
        )
        group = frappe._dict(
            {
                "group_based_on": "Course",
                "instructors": [
                    frappe._dict(
                        {
                            "instructor": "Instructor One",
                            "instructor_name": "Teacher One",
                        }
                    )
                ],
            }
        )

        with (
            patch("ifitwala_ed.schedule.student_group_scheduling.frappe.get_cached_doc", return_value=schedule),
            patch("ifitwala_ed.schedule.student_group_scheduling.frappe.get_doc", return_value=group),
        ):
            payload = fetch_block_grid(schedule_name="Schedule-1", sg="SG-1")

        self.assertEqual(payload["instructors"], [{"value": "Instructor One", "label": "Teacher One"}])
        self.assertIsNone(payload["grid"][1][0]["warning_message"])
        self.assertEqual(payload["grid"][1][1]["warning_label"], "Lunch Break")
        self.assertIn("Lunch Break", payload["grid"][1][1]["warning_message"])
