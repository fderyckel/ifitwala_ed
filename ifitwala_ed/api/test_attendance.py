# ifitwala_ed/api/test_attendance.py

from datetime import date
from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import student_attendance
from ifitwala_ed.api.attendance import (
    _clean_optional,
    _get_ledger_payload,
    _hash_list,
    _normalize_heatmap_mode,
    _normalize_thresholds,
)


class TestAttendanceApi(TestCase):
    @patch("ifitwala_ed.api.student_attendance.get_weekend_days_for_calendar")
    @patch("ifitwala_ed.api.student_attendance.resolve_student_group_schedule_name")
    @patch("ifitwala_ed.api.student_attendance.frappe.db.get_value")
    def test_get_weekend_days_uses_effective_schedule_when_group_schedule_missing(
        self,
        mock_get_value,
        mock_resolve_schedule,
        mock_get_weekend_days_for_calendar,
    ):
        mock_resolve_schedule.return_value = "SCH-SCHED-FALLBACK"
        mock_get_value.return_value = "CAL-001"
        mock_get_weekend_days_for_calendar.return_value = [5, 6]

        result = student_attendance.get_weekend_days("SG-001")

        self.assertEqual(result, [5, 6])
        mock_resolve_schedule.assert_called_once_with("SG-001")
        mock_get_value.assert_called_once_with("School Schedule", "SCH-SCHED-FALLBACK", "school_calendar")
        mock_get_weekend_days_for_calendar.assert_called_once_with("CAL-001")

    @patch("ifitwala_ed.api.attendance._resolve_school_threshold_defaults")
    def test_normalize_thresholds_uses_school_defaults_not_client_override(self, mock_defaults):
        mock_defaults.return_value = (92.0, 81.0)

        payload = _normalize_thresholds(
            {"warning": 10, "critical": 5},
            selected_school="SCH-1",
        )

        self.assertEqual(payload, {"warning": 92.0, "critical": 81.0})

    @patch("ifitwala_ed.api.attendance._resolve_school_threshold_defaults")
    def test_normalize_thresholds_swaps_when_warning_below_critical(self, mock_defaults):
        mock_defaults.return_value = (70.0, 85.0)

        payload = _normalize_thresholds(None, selected_school="SCH-1")

        self.assertEqual(payload, {"warning": 85.0, "critical": 70.0})

    def test_normalize_heatmap_mode_defaults_to_block(self):
        self.assertEqual(_normalize_heatmap_mode("day"), "day")
        self.assertEqual(_normalize_heatmap_mode("invalid"), "block")

    def test_clean_optional_and_hash_list_helpers(self):
        self.assertEqual(_clean_optional("  abc  "), "abc")
        self.assertIsNone(_clean_optional("   "))
        self.assertNotEqual(_hash_list(["a", "b"]), _hash_list(["a", "c"]))

    @patch("ifitwala_ed.api.attendance.frappe.get_all")
    @patch("ifitwala_ed.api.attendance.frappe.db.sql")
    def test_get_ledger_payload_returns_canonical_grouped_contract(
        self,
        mock_sql,
        mock_get_all,
    ):
        mock_get_all.return_value = [
            frappe._dict(
                {
                    "name": "ATT-CODE-P",
                    "attendance_code": "P",
                    "attendance_code_name": "Present",
                    "count_as_present": 1,
                    "display_order": 1,
                }
            ),
            frappe._dict(
                {
                    "name": "ATT-CODE-L",
                    "attendance_code": "L",
                    "attendance_code_name": "Late",
                    "count_as_present": 1,
                    "display_order": 2,
                }
            ),
            frappe._dict(
                {
                    "name": "ATT-CODE-A",
                    "attendance_code": "A",
                    "attendance_code_name": "Absent",
                    "count_as_present": 0,
                    "display_order": 3,
                }
            ),
        ]

        def fake_sql(query, params=None, as_dict=False):
            self.assertTrue(as_dict)
            if "LIMIT %(limit)s OFFSET %(offset)s" in query:
                self.assertEqual(params["limit"], 80)
                self.assertEqual(params["offset"], 0)
                self.assertIn("a.school IN %(school_scope)s", query)
                self.assertIn("a.attendance_date IN %(instruction_days)s", query)
                return [
                    frappe._dict(
                        {
                            "student": "STU-1",
                            "student_label": "Amina Dar",
                            "attendance_type": "Course",
                            "course": "COURSE-1",
                            "student_group": "SG-1",
                            "code_p_1": 8,
                            "code_l_2": 1,
                            "code_a_3": 2,
                            "present_count": 9,
                            "total_count": 11,
                            "percentage_present": 81.8,
                            "percentage_late": 11.1,
                        }
                    )
                ]
            if "COUNT(*) AS total_rows" in query:
                return [frappe._dict({"total_rows": 1})]
            if "COUNT(DISTINCT a.student) AS total_students" in query:
                return [
                    frappe._dict(
                        {
                            "raw_records": 11,
                            "total_students": 1,
                            "total_present": 9,
                            "total_late_present": 1,
                            "total_attendance": 11,
                        }
                    )
                ]
            if "SELECT DISTINCT a.course" in query:
                return [frappe._dict({"course": "COURSE-1"})]
            if "SELECT DISTINCT a.instructor" in query:
                return [frappe._dict({"instructor": "EMP-1"})]
            if "AS student_name" in query:
                return [frappe._dict({"student": "STU-1", "student_name": "Amina Dar"})]
            raise AssertionError(f"Unexpected SQL query: {query}")

        mock_sql.side_effect = fake_sql

        ctx = {
            "user": "admin@example.com",
            "role_class": "admin",
            "school_scope": ["SCH-PARENT", "SCH-CHILD"],
            "group_scope": [],
            "student_scope": [],
            "date_from": date(2026, 3, 1),
            "date_to": date(2026, 3, 31),
            "window_source": "selected_term",
            "academic_year": "AY-2026",
            "term": "TERM-1",
            "selected_school": "SCH-PARENT",
            "program": None,
            "program_scope": [],
            "student_group": None,
            "whole_day": 0,
            "activity_only": 0,
        }

        payload = _get_ledger_payload(
            ctx,
            course=None,
            instructor=None,
            student=None,
            attendance_code=None,
            page=1,
            page_length=80,
            sort_by="student_label",
            sort_order="asc",
        )

        self.assertEqual(payload["meta"]["window_source"], "selected_term")
        self.assertEqual(payload["pagination"], {"page": 1, "page_length": 80, "total_rows": 1, "total_pages": 1})
        self.assertEqual(payload["summary"]["percentage_present"], 81.8)
        self.assertEqual(payload["summary"]["percentage_late"], 11.1)
        self.assertEqual(payload["rows"][0]["student_label"], "Amina Dar")
        self.assertEqual(payload["rows"][0]["code_p_1"], 8)
        self.assertEqual(payload["filter_options"]["courses"], ["COURSE-1"])
        self.assertEqual(payload["filter_options"]["instructors"], ["EMP-1"])
        self.assertEqual(payload["filter_options"]["students"], [{"student": "STU-1", "student_name": "Amina Dar"}])
        self.assertEqual(
            payload["codes"],
            [
                {"attendance_code": "P", "attendance_code_name": "Present", "count_as_present": 1},
                {"attendance_code": "L", "attendance_code_name": "Late", "count_as_present": 1},
                {"attendance_code": "A", "attendance_code_name": "Absent", "count_as_present": 0},
            ],
        )
        self.assertEqual(
            [column["fieldname"] for column in payload["columns"][:7]],
            [
                "student_label",
                "attendance_type",
                "course",
                "student_group",
                "code_p_1",
                "code_l_2",
                "code_a_3",
            ],
        )

    @patch("ifitwala_ed.api.student_attendance._cached_context", side_effect=lambda _k, _r, builder: builder())
    @patch("ifitwala_ed.api.student_attendance.fetch_portal_terms")
    @patch("ifitwala_ed.api.student_attendance.fetch_portal_academic_years")
    @patch("ifitwala_ed.api.student_attendance.fetch_portal_student_groups")
    @patch("ifitwala_ed.api.student_attendance.fetch_active_programs")
    @patch("ifitwala_ed.api.student_attendance.fetch_school_filter_context")
    def test_fetch_attendance_ledger_context_aggregates_lists(
        self,
        mock_school_context,
        mock_programs,
        mock_groups,
        mock_years,
        mock_terms,
        _mock_cached,
    ):
        mock_school_context.return_value = {
            "default_school": "SCH-1",
            "schools": [{"name": "SCH-1", "school_name": "School 1"}],
        }
        mock_programs.return_value = [{"name": "PROG-1", "program_name": "Program 1"}]
        mock_groups.return_value = [{"name": "SG-1", "academic_year": "AY-2025"}]
        mock_years.return_value = []
        mock_terms.return_value = [{"name": "TERM-1"}]

        payload = student_attendance.fetch_attendance_ledger_context(program="PROG-1")

        self.assertEqual(payload["default_school"], "SCH-1")
        self.assertEqual(payload["default_program"], "PROG-1")
        self.assertEqual(payload["default_academic_year"], "AY-2025")
        self.assertEqual(payload["student_groups"], [{"name": "SG-1", "academic_year": "AY-2025"}])
        self.assertEqual(payload["terms"], [{"name": "TERM-1"}])
        mock_programs.assert_called_once_with(school="SCH-1")
        mock_terms.assert_called_once_with(academic_year="AY-2025", school="SCH-1")

    @patch("ifitwala_ed.api.student_attendance._expand_school_scope")
    @patch("ifitwala_ed.api.student_attendance.frappe.db.sql")
    def test_fetch_active_programs_scopes_to_program_offering_lineage_for_selected_school(
        self,
        mock_sql,
        mock_expand_school_scope,
    ):
        mock_expand_school_scope.return_value = ["SCH-1"]
        mock_sql.return_value = [
            frappe._dict({"name": "PROG-PARENT", "program_name": "Parent Program", "is_group": 1}),
            frappe._dict({"name": "PROG-CHILD", "program_name": "Child Program", "is_group": 0}),
            frappe._dict({"name": "PROG-SIBLING", "program_name": "Sibling Program", "is_group": 0}),
        ]

        rows = student_attendance.fetch_active_programs(school="SCH-1")

        self.assertEqual([row["name"] for row in rows], ["PROG-PARENT", "PROG-CHILD", "PROG-SIBLING"])
        self.assertIn("FROM `tabProgram Offering` po", mock_sql.call_args.args[0])
        query_params = mock_sql.call_args.args[1]
        self.assertEqual(query_params["school_scope"], ("SCH-1",))

    @patch("ifitwala_ed.api.student_attendance._expand_school_scope")
    @patch("ifitwala_ed.api.student_attendance.frappe.db.sql")
    def test_fetch_active_programs_returns_empty_when_selected_school_is_out_of_scope(
        self,
        mock_sql,
        mock_expand_school_scope,
    ):
        mock_expand_school_scope.return_value = []

        rows = student_attendance.fetch_active_programs(school="SCH-1")

        self.assertEqual(rows, [])
        mock_sql.assert_not_called()

    @patch("ifitwala_ed.api.student_attendance._cached_context", side_effect=lambda _k, _r, builder: builder())
    @patch("ifitwala_ed.api.student_attendance.list_attendance_codes")
    @patch("ifitwala_ed.api.student_attendance.fetch_portal_student_groups")
    @patch("ifitwala_ed.api.student_attendance.fetch_active_programs")
    @patch("ifitwala_ed.api.student_attendance.fetch_school_filter_context")
    def test_fetch_attendance_tool_bootstrap_auto_picks_single_group(
        self,
        mock_school_context,
        mock_programs,
        mock_groups,
        mock_codes,
        _mock_cached,
    ):
        mock_school_context.return_value = {
            "default_school": "SCH-1",
            "schools": [{"name": "SCH-1", "school_name": "School 1"}],
        }
        mock_programs.return_value = [{"name": "PROG-1", "program_name": "Program 1"}]
        mock_groups.return_value = [{"name": "SG-ONLY", "student_group_name": "Only Group"}]
        mock_codes.return_value = [
            {
                "name": "P",
                "attendance_code": "P",
                "attendance_code_name": "Present",
                "is_default": 1,
            }
        ]

        payload = student_attendance.fetch_attendance_tool_bootstrap()

        self.assertEqual(payload["default_student_group"], "SG-ONLY")
        self.assertEqual(payload["default_code"], "P")
        self.assertEqual(payload["attendance_codes"][0]["attendance_code_name"], "Present")
        mock_programs.assert_called_once_with(school="SCH-1")

    @patch("ifitwala_ed.api.student_attendance._cached_context", side_effect=lambda _k, _r, builder: builder())
    @patch("ifitwala_ed.api.student_attendance.list_attendance_codes")
    @patch("ifitwala_ed.api.student_attendance.fetch_portal_student_groups")
    @patch("ifitwala_ed.api.student_attendance.fetch_active_programs")
    @patch("ifitwala_ed.api.student_attendance.fetch_school_filter_context")
    def test_fetch_attendance_tool_bootstrap_falls_back_to_all_codes_when_tool_filter_is_empty(
        self,
        mock_school_context,
        mock_programs,
        mock_groups,
        mock_codes,
        _mock_cached,
    ):
        mock_school_context.return_value = {
            "default_school": "SCH-1",
            "schools": [{"name": "SCH-1", "school_name": "School 1"}],
        }
        mock_programs.return_value = [{"name": "PROG-1", "program_name": "Program 1"}]
        mock_groups.return_value = [{"name": "SG-1", "student_group_name": "Group 1"}]
        mock_codes.side_effect = [
            [],
            [{"name": "P", "attendance_code": "P", "attendance_code_name": "Present"}],
        ]

        payload = student_attendance.fetch_attendance_tool_bootstrap()

        self.assertEqual(payload["default_code"], "P")
        self.assertEqual(payload["attendance_codes"][0]["attendance_code"], "P")
        self.assertEqual(mock_codes.call_count, 2)
        self.assertEqual(mock_codes.call_args_list[1].kwargs, {"show_in_attendance_tool": None})
        mock_programs.assert_called_once_with(school="SCH-1")

    @patch("ifitwala_ed.api.student_attendance._cached_context", side_effect=lambda _k, _r, builder: builder())
    @patch("ifitwala_ed.api.student_attendance.list_attendance_codes")
    @patch("ifitwala_ed.api.student_attendance.fetch_portal_student_groups")
    @patch("ifitwala_ed.api.student_attendance.fetch_active_programs")
    @patch("ifitwala_ed.api.student_attendance.fetch_school_filter_context")
    def test_fetch_attendance_tool_bootstrap_prefers_code_marked_default(
        self,
        mock_school_context,
        mock_programs,
        mock_groups,
        mock_codes,
        _mock_cached,
    ):
        mock_school_context.return_value = {
            "default_school": "SCH-1",
            "schools": [{"name": "SCH-1", "school_name": "School 1"}],
        }
        mock_programs.return_value = [{"name": "PROG-1", "program_name": "Program 1"}]
        mock_groups.return_value = [{"name": "SG-1", "student_group_name": "Group 1"}]
        mock_codes.return_value = [
            {"name": "A", "attendance_code": "A", "attendance_code_name": "Absent", "is_default": 0},
            {"name": "P", "attendance_code": "P", "attendance_code_name": "Present", "is_default": 1},
        ]

        payload = student_attendance.fetch_attendance_tool_bootstrap()

        self.assertEqual(payload["default_code"], "P")
        mock_programs.assert_called_once_with(school="SCH-1")

    @patch("ifitwala_ed.api.student_attendance.attendance_recorded_dates")
    @patch("ifitwala_ed.api.student_attendance.get_meeting_dates")
    @patch("ifitwala_ed.api.student_attendance.get_weekend_days")
    @patch("ifitwala_ed.api.student_attendance.nowdate", return_value="2026-03-12")
    def test_fetch_attendance_tool_group_context_picks_last_past_date(
        self,
        _mock_nowdate,
        mock_weekend_days,
        mock_meeting_dates,
        mock_recorded_dates,
    ):
        mock_weekend_days.return_value = [6, 0]
        mock_meeting_dates.return_value = ["2026-03-10", "2026-03-12", "2026-03-15"]
        mock_recorded_dates.return_value = ["2026-03-10"]

        payload = student_attendance.fetch_attendance_tool_group_context("SG-1")

        self.assertEqual(payload["default_selected_date"], "2026-03-12")
        self.assertEqual(payload["recorded_dates"], ["2026-03-10"])

    @patch("ifitwala_ed.api.student_attendance.fetch_blocks_for_day")
    @patch("ifitwala_ed.api.student_attendance.fetch_existing_attendance")
    @patch("ifitwala_ed.api.student_attendance.previous_status_map")
    @patch("ifitwala_ed.api.student_attendance.fetch_students")
    def test_fetch_attendance_tool_roster_context_aggregates_day_payload(
        self,
        mock_fetch_students,
        mock_previous_status,
        mock_existing,
        mock_blocks,
    ):
        mock_fetch_students.return_value = {"students": [], "total": 0, "start": 0, "group_info": {}}
        mock_previous_status.return_value = {"STU-1|-1": "P"}
        mock_existing.return_value = {"STU-1": {-1: {"code": "P", "remark": ""}}}
        mock_blocks.return_value = [-1]

        payload = student_attendance.fetch_attendance_tool_roster_context("SG-1", "2026-03-12")

        self.assertEqual(payload["roster"]["total"], 0)
        self.assertEqual(payload["prev_map"], {"STU-1|-1": "P"})
        self.assertEqual(payload["existing_map"]["STU-1"][-1]["code"], "P")
        self.assertEqual(payload["blocks"], [-1])
