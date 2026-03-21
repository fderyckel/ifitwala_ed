# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import academic_load


class TestAcademicLoadApi(FrappeTestCase):
    def test_resolve_scope_rejects_school_outside_authorized_set(self):
        with patch.object(academic_load, "get_authorized_schools", return_value=["SCH-1"]):
            with self.assertRaises(frappe.PermissionError):
                academic_load._resolve_scope({"school": "SCH-2"}, "staff@example.com")

    def test_build_rows_excludes_activity_groups_from_student_adjustment(self):
        policy = SimpleNamespace(
            meeting_window_days=30,
            future_horizon_days=14,
            meeting_blend_mode="Blended Past + Future",
            teaching_weight=1.0,
            student_weight=1.0,
            student_ratio_divisor=15.0,
            activity_weight=1.0,
            meeting_weight=0.75,
            school_event_weight=0.75,
            underutilized_threshold=12.0,
            high_load_threshold=24.0,
            overload_threshold=30.0,
        )

        filters = {"time_mode": "current_week"}
        scope = {"school_scope": ["SCH-1"]}
        start_dt = datetime(2026, 3, 16, 8, 0, 0)
        end_dt = datetime(2026, 3, 16, 10, 0, 0)

        with (
            patch.object(
                academic_load,
                "_load_educators",
                return_value=[
                    {
                        "name": "EMP-1",
                        "employee_full_name": "Ada Staff",
                        "school": "SCH-1",
                        "user_id": "ada@example.com",
                        "employee_group": "Academic",
                        "roles": ["Academic Staff"],
                    }
                ],
            ),
            patch.object(academic_load, "_window_bounds", return_value=(date(2026, 3, 16), date(2026, 3, 22))),
            patch.object(
                academic_load,
                "_load_student_group_booking_rows",
                return_value=[
                    {
                        "employee": "EMP-1",
                        "from_datetime": start_dt,
                        "to_datetime": end_dt,
                        "student_group": "SG-COURSE",
                        "student_group_name": "Physics 8A",
                        "group_based_on": "Course",
                        "course": "COURSE-1",
                        "program": "PROG-1",
                        "program_offering": "PO-1",
                        "school": "SCH-1",
                    },
                    {
                        "employee": "EMP-1",
                        "from_datetime": start_dt,
                        "to_datetime": end_dt,
                        "student_group": "SG-ACTIVITY",
                        "student_group_name": "Debate Club",
                        "group_based_on": "Activity",
                        "course": None,
                        "program": "PROG-1",
                        "program_offering": "PO-1",
                        "school": "SCH-1",
                    },
                ],
            ),
            patch.object(
                academic_load, "_load_group_student_counts", return_value={"SG-COURSE": 18, "SG-ACTIVITY": 40}
            ),
            patch.object(academic_load, "_load_meeting_rows", return_value=[]),
            patch.object(academic_load, "_load_school_event_rows", return_value=[]),
            patch.object(academic_load, "_load_hard_booking_rows", return_value=[]),
            patch.object(academic_load, "_count_free_blocks", return_value={"EMP-1": 3}),
        ):
            rows, _meta = academic_load._build_rows(filters, scope, "AY-2026", policy)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["facts"]["students_taught"], 18)
        self.assertGreater(rows[0]["facts"]["activity_hours"], 0)

    def test_dashboard_strips_internal_detail_rows(self):
        cache = MagicMock()
        cache.get_value.return_value = None
        policy = {"name": "POL-1", "school": "SCH-1"}
        with (
            patch.object(academic_load, "_ensure_access", return_value="staff@example.com"),
            patch.object(
                academic_load,
                "_build_dataset",
                return_value={
                    "policy": policy,
                    "summary": {"staff_count": 1},
                    "kpis": [{"id": "staff_count", "label": "Staff in Scope", "value": 1}],
                    "rows": [
                        {
                            "educator": {"employee": "EMP-1", "full_name": "Ada Staff", "school": "SCH-1"},
                            "facts": {
                                "teaching_hours": 12,
                                "students_taught": 18,
                                "activity_hours": 2,
                                "meeting_weekly_avg_hours": 1,
                                "event_weekly_avg_hours": 0.5,
                                "free_blocks_count": 3,
                            },
                            "scores": {"total_load_score": 20, "teaching_units": 12, "non_teaching_units": 3.5},
                            "bands": {"load_band": "Normal"},
                            "availability": {"free_blocks_count": 3},
                            "_detail": {"teaching": {}},
                        }
                    ],
                    "fairness": {"distribution": [], "scatter": [], "ranked": []},
                    "effective_filters": {"school": "SCH-1"},
                    "meta": {"window": {"start_date": "2026-03-16", "end_date": "2026-03-22"}},
                },
            ),
            patch.object(academic_load.frappe, "cache", return_value=cache),
        ):
            payload = academic_load.get_academic_load_dashboard(payload={"school": "SCH-1"})

        self.assertEqual(payload["rows"][0]["educator"]["employee"], "EMP-1")
        self.assertNotIn("_detail", payload["rows"][0])

    def test_cover_candidates_rank_exact_match_before_lower_fit(self):
        dataset_rows = [
            {
                "educator": {"employee": "EMP-1", "full_name": "Exact Match", "school": "SCH-1"},
                "facts": {"free_blocks_count": 3},
                "scores": {"total_load_score": 22.0},
            },
            {
                "educator": {"employee": "EMP-2", "full_name": "Course Match", "school": "SCH-1"},
                "facts": {"free_blocks_count": 4},
                "scores": {"total_load_score": 18.0},
            },
            {
                "educator": {"employee": "EMP-3", "full_name": "Unavailable", "school": "SCH-1"},
                "facts": {"free_blocks_count": 0},
                "scores": {"total_load_score": 10.0},
            },
        ]

        with (
            patch.object(academic_load, "_ensure_access", return_value="staff@example.com"),
            patch.object(academic_load, "_build_dataset", return_value={"rows": dataset_rows}),
            patch.object(academic_load, "_resolve_scope", return_value={"school_scope": ["SCH-1"]}),
            patch.object(
                academic_load.frappe.db,
                "get_value",
                return_value=frappe._dict(
                    {
                        "name": "SG-1",
                        "student_group_name": "Physics 8A",
                        "school": "SCH-1",
                        "course": "COURSE-1",
                        "program": "PROG-1",
                        "academic_year": "AY-1",
                    }
                ),
            ),
            patch.object(
                academic_load.frappe.db,
                "sql",
                return_value=[
                    {"employee": "EMP-1", "student_group": "SG-1", "course": "COURSE-1", "program": "PROG-1"},
                    {"employee": "EMP-2", "student_group": "SG-2", "course": "COURSE-1", "program": "PROG-2"},
                ],
            ),
            patch.object(
                academic_load,
                "_load_hard_booking_rows",
                return_value=[
                    {
                        "employee": "EMP-3",
                        "from_datetime": datetime(2026, 3, 21, 9, 0, 0),
                        "to_datetime": datetime(2026, 3, 21, 10, 0, 0),
                    }
                ],
            ),
            patch.object(
                academic_load.frappe,
                "cache",
                return_value=MagicMock(get_value=lambda key: None, set_value=lambda *args, **kwargs: None),
            ),
        ):
            payload = academic_load.get_academic_load_cover_candidates(
                payload={"school": "SCH-1"},
                student_group="SG-1",
                from_datetime="2026-03-21 09:00:00",
                to_datetime="2026-03-21 10:00:00",
            )

        self.assertEqual(payload["rows"][0]["educator"]["employee"], "EMP-1")
        self.assertEqual(payload["rows"][0]["cover_suitability"], "Strong fit")
        self.assertEqual(payload["rows"][1]["educator"]["employee"], "EMP-2")
        self.assertEqual(payload["rows"][1]["cover_suitability"], "Possible")
        self.assertEqual(payload["rows"][-1]["educator"]["employee"], "EMP-3")
        self.assertEqual(payload["rows"][-1]["cover_suitability"], "Unavailable")
