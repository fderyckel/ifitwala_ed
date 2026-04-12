# Copyright (c) 2024, fdR and Contributors
# See license.txt

# ifitwala_ed/schedule/doctype/student_group/test_student_group.py

from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.curriculum import planning
from ifitwala_ed.schedule.doctype.student_group.student_group import (
    StudentGroup,
    build_in_clause_placeholders,
    descendants_inclusive,
    get_single_offering_academic_year,
    instructor_log_sync_context,
    is_same_or_descendant,
    schedule_location_query,
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

    @patch("ifitwala_ed.curriculum.planning.bootstrap_student_group_class_teaching_plan")
    def test_after_insert_bootstraps_class_teaching_plan(self, mock_bootstrap):
        group = object.__new__(StudentGroup)

        group.after_insert()

        mock_bootstrap.assert_called_once_with(group)

    def test_normalize_group_anchor_fields_clears_course_for_non_course_groups(self):
        group = object.__new__(StudentGroup)
        group.group_based_on = "Activity"
        group.course = "COURSE-1"

        StudentGroup._normalize_group_anchor_fields(group)

        self.assertIsNone(group.course)

    @patch("ifitwala_ed.curriculum.planning.frappe.logger")
    @patch("ifitwala_ed.curriculum.planning.frappe.new_doc")
    @patch("ifitwala_ed.curriculum.planning.frappe.get_all")
    @patch("ifitwala_ed.curriculum.planning.frappe.db.get_value")
    def test_bootstrap_student_group_class_teaching_plan_creates_active_plan_for_unambiguous_course_plan(
        self,
        mock_get_value,
        mock_get_all,
        mock_new_doc,
        mock_logger,
    ):
        class FakePlan:
            def __init__(self):
                self.name = "CLASS-PLAN-1"
                self.student_group = None
                self.course_plan = None
                self.planning_status = None
                self.insert_calls = []

            def insert(self, ignore_permissions=False):
                self.insert_calls.append(ignore_permissions)

        group = frappe._dict(
            {
                "name": "SG-1",
                "group_based_on": "Course",
                "status": "Active",
                "course": "COURSE-1",
                "academic_year": "AY-2026",
            }
        )
        class_plan = FakePlan()
        mock_get_all.return_value = [{"name": "COURSE-PLAN-1"}]
        mock_get_value.return_value = None
        mock_new_doc.return_value = class_plan
        mock_logger.return_value = frappe._dict({"info": lambda _payload: None})

        result = planning.bootstrap_student_group_class_teaching_plan(group)

        mock_get_all.assert_called_once_with(
            "Course Plan",
            filters={
                "course": "COURSE-1",
                "plan_status": ["!=", "Archived"],
                "academic_year": "AY-2026",
            },
            fields=["name"],
            order_by="modified desc, creation desc",
            limit=2,
        )
        mock_new_doc.assert_called_once_with("Class Teaching Plan")
        self.assertEqual(class_plan.student_group, "SG-1")
        self.assertEqual(class_plan.course_plan, "COURSE-PLAN-1")
        self.assertEqual(class_plan.planning_status, "Active")
        self.assertEqual(class_plan.insert_calls, [True])
        self.assertEqual(
            result,
            {
                "status": "created",
                "reason": None,
                "student_group": "SG-1",
                "course_plan": "COURSE-PLAN-1",
                "class_teaching_plan": "CLASS-PLAN-1",
            },
        )

    @patch("ifitwala_ed.curriculum.planning.frappe.logger")
    @patch("ifitwala_ed.curriculum.planning.frappe.new_doc")
    @patch("ifitwala_ed.curriculum.planning.frappe.get_all")
    @patch("ifitwala_ed.curriculum.planning.frappe.db.get_value")
    def test_bootstrap_student_group_class_teaching_plan_skips_when_course_plan_is_ambiguous(
        self,
        mock_get_value,
        mock_get_all,
        mock_new_doc,
        mock_logger,
    ):
        group = frappe._dict(
            {
                "name": "SG-1",
                "group_based_on": "Course",
                "status": "Active",
                "course": "COURSE-1",
                "academic_year": "AY-2026",
            }
        )
        mock_get_all.side_effect = [
            [],
            [{"name": "COURSE-PLAN-1"}, {"name": "COURSE-PLAN-2"}],
        ]
        mock_logger.return_value = frappe._dict({"info": lambda _payload: None})

        result = planning.bootstrap_student_group_class_teaching_plan(group)

        self.assertEqual(mock_get_all.call_count, 2)
        mock_get_value.assert_not_called()
        mock_new_doc.assert_not_called()
        self.assertEqual(
            result,
            {
                "status": "skipped",
                "reason": "multiple_course_plans",
                "student_group": "SG-1",
                "course_plan": None,
                "class_teaching_plan": None,
            },
        )


class TestStudentGroupScheduleAdvisories(FrappeTestCase):
    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.frappe.db.get_value")
    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.is_schedulable_location")
    def test_validate_schedule_locations_rejects_group_location(self, mock_is_schedulable_location, mock_get_value):
        group = frappe.get_doc(
            {
                "doctype": "Student Group",
                "school": "KIS Bangkok",
                "student_group_schedule": [
                    {
                        "rotation_day": 1,
                        "block_number": 3,
                        "location": "D204",
                    }
                ],
            }
        )
        mock_is_schedulable_location.return_value = False
        mock_get_value.return_value = frappe._dict({"name": "D204", "is_group": 1})

        with self.assertRaises(frappe.ValidationError) as exc:
            group._validate_schedule_locations()

        self.assertIn("group/container location", str(exc.exception))
        self.assertIn("D204", str(exc.exception))

    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.get_visible_location_rows_for_school")
    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.frappe.db.get_value")
    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.is_schedulable_location")
    def test_validate_schedule_locations_rejects_room_outside_visible_scope(
        self,
        mock_is_schedulable_location,
        mock_get_value,
        mock_get_visible_location_rows_for_school,
    ):
        group = frappe.get_doc(
            {
                "doctype": "Student Group",
                "school": "KIS Bangkok",
                "student_group_schedule": [
                    {
                        "rotation_day": 1,
                        "block_number": 3,
                        "location": "D204",
                    }
                ],
            }
        )
        mock_is_schedulable_location.return_value = True
        mock_get_value.return_value = frappe._dict({"name": "D204", "is_group": 0})
        mock_get_visible_location_rows_for_school.return_value = [{"name": "D203"}]

        with self.assertRaises(frappe.ValidationError) as exc:
            group._validate_schedule_locations()

        self.assertIn("outside the visible room scope", str(exc.exception))
        self.assertIn("KIS Bangkok", str(exc.exception))

    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.get_visible_location_rows_for_school")
    def test_schedule_location_query_returns_only_matching_schedulable_rooms(
        self,
        mock_get_visible_location_rows_for_school,
    ):
        mock_get_visible_location_rows_for_school.return_value = [
            {"name": "D203", "location_name": "D203"},
            {"name": "D204", "location_name": "D204"},
        ]

        rows = schedule_location_query(
            "Location",
            "204",
            "name",
            0,
            20,
            {"school": "KIS Bangkok"},
        )

        self.assertEqual(rows, [["D204"]])
        mock_get_visible_location_rows_for_school.assert_called_once_with(
            "KIS Bangkok",
            include_groups=False,
            only_schedulable=True,
            fields=["name", "location_name"],
            limit=2000,
            order_by="location_name asc",
        )

    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.get_rotation_dates")
    @patch("ifitwala_ed.schedule.doctype.student_group.student_group.find_room_conflicts")
    @patch.object(StudentGroup, "_get_school_schedule")
    def test_validate_location_conflicts_absolute_checks_exact_room_only(
        self,
        mock_get_school_schedule,
        mock_find_room_conflicts,
        mock_get_rotation_dates,
    ):
        group = frappe.get_doc(
            {
                "doctype": "Student Group",
                "name": "25-26-G6-Kafue",
                "academic_year": "IIS 2025-2026",
                "student_group_schedule": [
                    {
                        "rotation_day": 1,
                        "block_number": 3,
                        "location": "D201",
                    }
                ],
            }
        )
        mock_get_school_schedule.return_value = frappe._dict(
            {
                "school_schedule_block": [
                    frappe._dict(
                        {
                            "rotation_day": 1,
                            "block_number": 3,
                            "from_time": "09:40:00",
                            "to_time": "09:55:00",
                        }
                    )
                ]
            }
        )
        mock_get_rotation_dates.return_value = [{"rotation_day": 1, "date": "2025-08-07"}]
        mock_find_room_conflicts.return_value = []

        group.validate_location_conflicts_absolute()

        mock_find_room_conflicts.assert_called_once()
        self.assertEqual(mock_find_room_conflicts.call_args.kwargs.get("include_children"), False)

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

    def test_validate_schedule_rows_skips_warning_for_non_course_group(self):
        group = frappe.get_doc(
            {
                "doctype": "Student Group",
                "group_based_on": "Activity",
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
                            "description": "Assembly",
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
