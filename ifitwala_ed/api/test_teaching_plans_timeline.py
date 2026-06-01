from __future__ import annotations

from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api.teaching_plans_test_support import _teaching_plans_module


class TestTeachingPlansTimeline(TestCase):
    def test_build_course_plan_timeline_skips_holidays_and_blocks_after_unresolved_duration(self):
        with _teaching_plans_module() as module:

            def fake_get_all(doctype, *args, **kwargs):
                if doctype == "School Calendar Holidays":
                    return [
                        {"holiday_date": date(2026, 1, 19), "description": "Mid-year break"},
                        {"holiday_date": date(2026, 1, 20), "description": "Mid-year break"},
                        {"holiday_date": date(2026, 1, 21), "description": "Mid-year break"},
                        {"holiday_date": date(2026, 1, 22), "description": "Mid-year break"},
                        {"holiday_date": date(2026, 1, 23), "description": "Mid-year break"},
                    ]
                if doctype == "School Calendar Term":
                    return [
                        {
                            "term": "TERM-1",
                            "start": date(2026, 1, 5),
                            "end": date(2026, 1, 30),
                            "number_of_instructional_days": 20,
                        }
                    ]
                return []

            with (
                patch.object(
                    module,
                    "_resolve_course_plan_timeline_scope",
                    return_value={
                        "status": "ready",
                        "scope": {
                            "mode": "academic_year",
                            "academic_year": "2026-2027",
                            "school": "SCH-1",
                            "window_start": "2026-01-05",
                            "window_end": "2026-01-30",
                        },
                    },
                ),
                patch(
                    "ifitwala_ed.school_settings.school_settings_utils.resolve_school_calendars_for_window",
                    return_value=[{"name": "CAL-1", "academic_year": "2026-2027"}],
                ),
                patch("ifitwala_ed.schedule.schedule_utils.get_weekend_days_for_calendar", return_value=[0, 6]),
                patch(
                    "ifitwala_ed.schedule.schedule_utils.get_calendar_holiday_set",
                    return_value={
                        date(2026, 1, 19),
                        date(2026, 1, 20),
                        date(2026, 1, 21),
                        date(2026, 1, 22),
                        date(2026, 1, 23),
                    },
                ),
                patch.object(module.frappe, "get_all", side_effect=fake_get_all),
                patch.object(module, "now_datetime", return_value=datetime(2026, 1, 15, 9, 0, 0)),
            ):
                payload = module._build_course_plan_timeline(
                    {"course": "COURSE-1", "academic_year": "2026-2027", "school": "SCH-1"},
                    [
                        {
                            "unit_plan": "UNIT-1",
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "duration": "3 weeks",
                            "unit_status": "Active",
                            "is_published": 1,
                        },
                        {
                            "unit_plan": "UNIT-2",
                            "title": "Scientific Method",
                            "unit_order": 20,
                            "duration": "TBD",
                            "unit_status": "Draft",
                            "is_published": 0,
                        },
                        {
                            "unit_plan": "UNIT-3",
                            "title": "Lab Reflection",
                            "unit_order": 30,
                            "duration": "1 week",
                            "unit_status": "Draft",
                            "is_published": 0,
                        },
                    ],
                )

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["holidays"][0]["start_date"], "2026-01-19")
        self.assertEqual(payload["holidays"][0]["end_date"], "2026-01-23")
        self.assertEqual(payload["units"][0]["start_date"], "2026-01-05")
        self.assertEqual(payload["units"][0]["end_date"], "2026-01-30")
        self.assertEqual(payload["units"][0]["is_current"], 1)
        self.assertEqual(payload["units"][1]["schedule_state"], "unscheduled_duration")
        self.assertEqual(payload["units"][1]["is_current"], 0)
        self.assertEqual(payload["units"][2]["schedule_state"], "blocked")

    def test_resolve_timeline_current_unit_keeps_previous_unit_active_during_gap(self):
        with _teaching_plans_module() as module:
            current_unit = module._resolve_timeline_current_unit(
                {
                    "status": "ready",
                    "units": [
                        {
                            "unit_plan": "UNIT-1",
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "start_date": "2026-01-05",
                            "end_date": "2026-01-30",
                        },
                        {
                            "unit_plan": "UNIT-2",
                            "title": "Scientific Method",
                            "unit_order": 20,
                            "start_date": "2026-02-02",
                            "end_date": "2026-02-27",
                        },
                    ],
                },
                anchor_date="2026-01-31",
            )

        self.assertEqual(current_unit["unit_plan"], "UNIT-1")

    def test_fetch_timeline_holiday_spans_merges_weekend_inside_same_break(self):
        with _teaching_plans_module() as module:
            with patch.object(
                module.frappe,
                "get_all",
                return_value=[
                    {"holiday_date": date(2026, 1, 9), "description": "Mid-term break"},
                    {"holiday_date": date(2026, 1, 12), "description": "Mid-term break"},
                ],
            ):
                payload = module._fetch_timeline_holiday_spans(
                    "CAL-1",
                    window_start=date(2026, 1, 1),
                    window_end=date(2026, 1, 31),
                    weekend_days=[0, 6],
                )

        self.assertEqual(
            payload,
            [
                {
                    "start_date": "2026-01-09",
                    "end_date": "2026-01-12",
                    "titles": ["Mid-term break"],
                    "day_count": 4,
                }
            ],
        )

    def test_resolve_course_plan_timeline_scope_clamps_to_student_group_term(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(module, "_assert_staff_group_access", return_value=None),
                patch.object(
                    module.planning,
                    "get_student_group_row",
                    return_value={
                        "name": "GROUP-1",
                        "student_group_name": "Biology A",
                        "student_group_abbreviation": "BIO-A",
                        "course": "COURSE-1",
                        "academic_year": "2026-2027",
                        "school": "SCH-1",
                        "term": "TERM-1",
                    },
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    side_effect=[
                        {
                            "name": "2026-2027",
                            "year_start_date": date(2026, 1, 1),
                            "year_end_date": date(2026, 12, 31),
                        },
                        {
                            "name": "TERM-1",
                            "term_start_date": date(2026, 1, 5),
                            "term_end_date": date(2026, 3, 27),
                            "academic_year": "2026-2027",
                        },
                    ],
                ),
            ):
                payload = module._resolve_course_plan_timeline_scope(
                    {
                        "course": "COURSE-1",
                        "academic_year": "2026-2027",
                        "school": "SCH-1",
                    },
                    student_group="GROUP-1",
                )

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["scope"]["mode"], "student_group_term")
        self.assertEqual(payload["scope"]["student_group"], "GROUP-1")
        self.assertEqual(payload["scope"]["term"], "TERM-1")
        self.assertEqual(payload["scope"]["window_start"], "2026-01-05")
        self.assertEqual(payload["scope"]["window_end"], "2026-03-27")

    def test_resolve_course_plan_timeline_scope_can_use_student_authorized_class_context(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_assert_staff_group_access",
                    side_effect=AssertionError("student LMS timeline must not require staff class access"),
                ),
                patch.object(
                    module.planning,
                    "get_student_group_row",
                    return_value={
                        "name": "GROUP-1",
                        "student_group_name": "Biology A",
                        "student_group_abbreviation": "BIO-A",
                        "course": "COURSE-1",
                        "academic_year": "2026-2027",
                        "school": "SCH-1",
                        "term": "",
                    },
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={
                        "name": "2026-2027",
                        "year_start_date": date(2026, 1, 1),
                        "year_end_date": date(2026, 12, 31),
                    },
                ),
            ):
                payload = module._resolve_course_plan_timeline_scope(
                    {
                        "course": "COURSE-1",
                        "academic_year": "2026-2027",
                        "school": "SCH-1",
                    },
                    student_group="GROUP-1",
                    require_staff_access=False,
                )

        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["scope"]["student_group"], "GROUP-1")
        self.assertEqual(payload["scope"]["student_group_label"], "Biology A")
