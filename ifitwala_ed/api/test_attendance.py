# ifitwala_ed/api/test_attendance.py

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api import student_attendance
from ifitwala_ed.api.attendance import (
    _clean_optional,
    _hash_list,
    _normalize_heatmap_mode,
    _normalize_thresholds,
)


class TestAttendanceApi(TestCase):
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
        mock_terms.assert_called_once_with(academic_year="AY-2025", school="SCH-1")

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
