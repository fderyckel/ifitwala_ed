from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api.teaching_plans_test_support import _teaching_plans_module


class TestTeachingPlansStaff(TestCase):
    def test_build_staff_bundle_without_selected_plan_returns_empty_curriculum(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_staff_plan",
                    return_value=(
                        {
                            "name": "GROUP-1",
                            "student_group_name": "Biology A",
                            "course": "COURSE-1",
                            "academic_year": "2025-2026",
                        },
                        [{"name": "COURSE-PLAN-1", "title": "Semester 1", "plan_status": "Active"}],
                        [],
                        None,
                    ),
                ),
                patch.object(module, "now_datetime") as now_datetime,
            ):
                now_datetime.return_value.isoformat.return_value = "2026-03-31 10:00:00"
                payload = module._build_staff_bundle("GROUP-1")

        self.assertIsNone(payload["teaching_plan"])
        self.assertEqual(payload["curriculum"]["units"], [])
        self.assertEqual(payload["curriculum"]["session_count"], 0)

    def test_decorate_resolved_pacing_statuses_marks_units_relative_to_current_unit(self):
        with _teaching_plans_module() as module:
            payload = module._decorate_resolved_pacing_statuses(
                [
                    {"unit_plan": "UNIT-1", "unit_order": 10, "pacing_status": "Not Started"},
                    {"unit_plan": "UNIT-2", "unit_order": 20, "pacing_status": "Not Started"},
                    {"unit_plan": "UNIT-3", "unit_order": 30, "pacing_status": "Hold"},
                ],
                {
                    "unit_plan": "UNIT-2",
                    "source": "calendar",
                },
            )

        self.assertEqual(payload[0]["resolved_pacing_status"], "Completed")
        self.assertEqual(payload[1]["resolved_pacing_status"], "In Progress")
        self.assertEqual(payload[2]["resolved_pacing_status"], "Hold")

    def test_build_staff_bundle_exposes_resolved_current_unit(self):
        with _teaching_plans_module() as module:
            class_doc = SimpleNamespace(
                name="CLASS-PLAN-1",
                course_plan="COURSE-PLAN-1",
                title="Biology A Plan",
                planning_status="Active",
                team_note="",
                get=lambda fieldname, default=None: [] if fieldname == "units" else default,
            )
            with (
                patch.object(
                    module,
                    "_resolve_staff_plan",
                    return_value=(
                        {
                            "name": "GROUP-1",
                            "student_group_name": "Biology A",
                            "course": "COURSE-1",
                            "academic_year": "2026-2027",
                        },
                        [{"name": "COURSE-PLAN-1", "title": "Semester 1", "plan_status": "Active"}],
                        [
                            {
                                "name": "CLASS-PLAN-1",
                                "title": "Biology A Plan",
                                "course_plan": "COURSE-PLAN-1",
                                "planning_status": "Active",
                            }
                        ],
                        "CLASS-PLAN-1",
                    ),
                ),
                patch.object(module.frappe, "get_doc", return_value=class_doc),
                patch.object(
                    module,
                    "_build_unit_lookup",
                    return_value={
                        "UNIT-1": {"title": "Cells", "unit_order": 10},
                        "UNIT-2": {"title": "Scientific Method", "unit_order": 20},
                    },
                ),
                patch.object(
                    module,
                    "_serialize_backbone_units",
                    return_value=[
                        {"unit_plan": "UNIT-1", "title": "Cells", "unit_order": 10},
                        {"unit_plan": "UNIT-2", "title": "Scientific Method", "unit_order": 20},
                    ],
                ),
                patch.object(module, "_fetch_class_sessions", return_value=[]),
                patch.object(module, "_fetch_assigned_work", return_value=[]),
                patch.object(
                    module,
                    "_attach_resources_and_work",
                    return_value={
                        "shared_resources": [],
                        "class_resources": [],
                        "general_assigned_work": [],
                    },
                ),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={"name": "COURSE-PLAN-1", "course": "COURSE-1"},
                ),
                patch.object(
                    module,
                    "_resolve_current_curriculum_unit",
                    return_value={
                        "unit_plan": "UNIT-2",
                        "unit": {"unit_plan": "UNIT-2", "title": "Scientific Method"},
                        "source": "calendar",
                        "timeline": None,
                    },
                ),
            ):
                payload = module._build_staff_bundle("GROUP-1", "CLASS-PLAN-1")

        self.assertEqual(payload["resolved"]["unit_plan"], "UNIT-2")
