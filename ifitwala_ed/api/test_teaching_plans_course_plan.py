from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ifitwala_ed.api.teaching_plans_test_support import _teaching_plans_module


class TestTeachingPlansCoursePlan(TestCase):
    def test_build_staff_course_plan_bundle_includes_selected_unit_and_resources(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={
                        "anchor_doctype": "Course Plan",
                        "anchor_name": "COURSE-PLAN-1",
                        "can_manage_resources": 1,
                    },
                ),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={
                        "name": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                    },
                ),
                patch.object(
                    module.planning,
                    "get_unit_plan_rows",
                    return_value=[
                        {
                            "name": "UNIT-1",
                            "title": "Cells and Systems",
                            "unit_order": 10,
                        }
                    ],
                ),
                patch.object(
                    module,
                    "_build_unit_lookup",
                    return_value={
                        "UNIT-1": {
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "standards": [],
                            "shared_reflections": [],
                            "class_reflections": [],
                        }
                    },
                ),
                patch.object(
                    module,
                    "_fetch_material_map",
                    return_value={
                        ("Course Plan", "COURSE-PLAN-1"): [{"material": "MAT-COURSE", "title": "Scope and sequence"}],
                        ("Unit Plan", "UNIT-1"): [{"material": "MAT-UNIT", "title": "Lab handout"}],
                    },
                ),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(
                        name="COURSE-PLAN-1",
                        modified="2026-04-02 09:00:00",
                        summary="Shared course summary",
                        check_permission=lambda ptype: None,
                    ),
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={"course_name": "Biology", "course_group": "Science"},
                ),
                patch.object(
                    module,
                    "_fetch_academic_year_options_for_schools",
                    return_value={
                        "SCH-1": [
                            {"value": "2026-2027", "label": "2026-2027", "school": "SCH-1"},
                        ]
                    },
                ),
                patch.object(module, "_fetch_program_options_for_course", return_value=[]),
                patch.object(
                    module,
                    "_build_course_plan_timeline",
                    return_value={
                        "status": "ready",
                        "units": [{"unit_plan": "UNIT-1", "is_current": 1}],
                    },
                ),
            ):
                payload = module._build_staff_course_plan_bundle("COURSE-PLAN-1")

        self.assertEqual(payload["resolved"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["course_plan"]["can_manage_resources"], 1)
        self.assertEqual(payload["resources"]["course_plan_resources"][0]["title"], "Scope and sequence")
        self.assertEqual(payload["curriculum"]["units"][0]["shared_resources"][0]["title"], "Lab handout")

    def test_build_staff_course_plan_bundle_includes_quiz_bank_detail(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={
                        "anchor_doctype": "Course Plan",
                        "anchor_name": "COURSE-PLAN-1",
                        "can_manage_resources": 1,
                    },
                ),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={
                        "name": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                    },
                ),
                patch.object(
                    module.planning,
                    "get_unit_plan_rows",
                    return_value=[{"name": "UNIT-1", "title": "Cells and Systems", "unit_order": 10}],
                ),
                patch.object(
                    module,
                    "_build_unit_lookup",
                    return_value={
                        "UNIT-1": {
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "standards": [],
                            "shared_reflections": [],
                            "class_reflections": [],
                        }
                    },
                ),
                patch.object(module, "_fetch_material_map", return_value={}),
                patch.object(
                    module,
                    "_fetch_course_quiz_question_banks",
                    return_value=[
                        {
                            "quiz_question_bank": "QBK-1",
                            "bank_title": "Cells Check-in",
                            "question_count": 5,
                            "published_question_count": 4,
                            "is_published": 1,
                        }
                    ],
                ),
                patch.object(
                    module,
                    "_fetch_selected_quiz_question_bank",
                    return_value={
                        "quiz_question_bank": "QBK-1",
                        "bank_title": "Cells Check-in",
                        "questions": [{"quiz_question": "QQ-1", "title": "Where is the nucleus?", "options": []}],
                    },
                ),
                patch.object(
                    module,
                    "_fetch_academic_year_options_for_schools",
                    return_value={
                        "SCH-1": [
                            {"value": "2026-2027", "label": "2026-2027", "school": "SCH-1"},
                        ]
                    },
                ),
                patch.object(
                    module,
                    "_fetch_program_options_for_course",
                    return_value=[
                        {
                            "value": "MYP",
                            "label": "MYP",
                            "parent_program": None,
                            "is_group": 0,
                            "archived": 0,
                        }
                    ],
                ),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(
                        name="COURSE-PLAN-1",
                        modified="2026-04-02 09:00:00",
                        summary="Shared course summary",
                        check_permission=lambda ptype: None,
                    ),
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={"course_name": "Biology", "course_group": "Science"},
                ),
                patch.object(
                    module,
                    "_build_course_plan_timeline",
                    return_value={
                        "status": "ready",
                        "units": [{"unit_plan": "UNIT-1", "is_current": 1}],
                    },
                ),
            ):
                payload = module._build_staff_course_plan_bundle("COURSE-PLAN-1")

        self.assertEqual(payload["assessment"]["quiz_question_banks"][0]["quiz_question_bank"], "QBK-1")
        self.assertEqual(payload["field_options"]["academic_years"][0]["value"], "2026-2027")
        self.assertEqual(payload["field_options"]["programs"][0]["value"], "MYP")
        self.assertEqual(
            payload["assessment"]["selected_quiz_question_bank"]["questions"][0]["quiz_question"],
            "QQ-1",
        )

    def test_build_staff_course_plan_bundle_uses_course_linked_program_options_only(self):
        with _teaching_plans_module() as module:
            program_options_mock = Mock(return_value=[])

            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={
                        "anchor_doctype": "Course Plan",
                        "anchor_name": "COURSE-PLAN-1",
                        "can_manage_resources": 1,
                    },
                ),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={
                        "name": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                    },
                ),
                patch.object(
                    module,
                    "_build_unit_lookup",
                    return_value={
                        "UNIT-1": {
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "program": "LEGACY-PROGRAM",
                            "standards": [{"program": "LEGACY-STANDARDS-PROGRAM"}],
                            "shared_reflections": [],
                            "class_reflections": [],
                        }
                    },
                ),
                patch.object(module, "_fetch_material_map", return_value={}),
                patch.object(module, "_fetch_course_quiz_question_banks", return_value=[]),
                patch.object(module, "_fetch_selected_quiz_question_bank", return_value=None),
                patch.object(
                    module,
                    "_fetch_academic_year_options_for_schools",
                    return_value={
                        "SCH-1": [
                            {"value": "2026-2027", "label": "2026-2027", "school": "SCH-1"},
                        ]
                    },
                ),
                patch.object(module, "_fetch_program_options_for_course", program_options_mock),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(
                        name="COURSE-PLAN-1",
                        modified="2026-04-02 09:00:00",
                        summary="Shared course summary",
                        check_permission=lambda ptype: None,
                    ),
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={"course_name": "Biology", "course_group": "Science"},
                ),
                patch.object(
                    module,
                    "_build_course_plan_timeline",
                    return_value={
                        "status": "ready",
                        "units": [{"unit_plan": "UNIT-1", "is_current": 1}],
                    },
                ),
            ):
                payload = module._build_staff_course_plan_bundle("COURSE-PLAN-1")

        program_options_mock.assert_called_once_with("COURSE-1")
        self.assertEqual(payload["field_options"]["programs"], [])

    def test_build_staff_course_plan_bundle_uses_scope_only_academic_year_options(self):
        with _teaching_plans_module() as module:
            academic_year_options_mock = Mock(return_value={"SCH-1": []})

            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={
                        "anchor_doctype": "Course Plan",
                        "anchor_name": "COURSE-PLAN-1",
                        "can_manage_resources": 1,
                    },
                ),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={
                        "name": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "SCH-OTHER 2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                    },
                ),
                patch.object(
                    module,
                    "_build_unit_lookup",
                    return_value={
                        "UNIT-1": {
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "standards": [],
                            "shared_reflections": [],
                            "class_reflections": [],
                        }
                    },
                ),
                patch.object(module, "_fetch_material_map", return_value={}),
                patch.object(module, "_fetch_course_quiz_question_banks", return_value=[]),
                patch.object(module, "_fetch_selected_quiz_question_bank", return_value=None),
                patch.object(module, "_fetch_academic_year_options_for_schools", academic_year_options_mock),
                patch.object(module, "_fetch_program_options_for_course", return_value=[]),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(
                        name="COURSE-PLAN-1",
                        modified="2026-04-02 09:00:00",
                        summary="Shared course summary",
                        check_permission=lambda ptype: None,
                    ),
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={"course_name": "Biology", "course_group": "Science"},
                ),
                patch.object(
                    module,
                    "_build_course_plan_timeline",
                    return_value={
                        "status": "ready",
                        "units": [{"unit_plan": "UNIT-1", "is_current": 1}],
                    },
                ),
            ):
                payload = module._build_staff_course_plan_bundle("COURSE-PLAN-1")

        academic_year_options_mock.assert_called_once_with(["SCH-1"])
        self.assertEqual(payload["field_options"]["academic_years"], [])

    def test_build_staff_course_plan_bundle_defaults_to_current_timeline_unit(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={
                        "anchor_doctype": "Course Plan",
                        "anchor_name": "COURSE-PLAN-1",
                        "can_manage_resources": 1,
                    },
                ),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={
                        "name": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                    },
                ),
                patch.object(
                    module.planning,
                    "get_unit_plan_rows",
                    return_value=[
                        {"name": "UNIT-1", "title": "Cells and Systems", "unit_order": 10},
                        {"name": "UNIT-2", "title": "Scientific Method", "unit_order": 20},
                    ],
                ),
                patch.object(
                    module,
                    "_build_unit_lookup",
                    return_value={
                        "UNIT-1": {
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "standards": [],
                            "shared_reflections": [],
                            "class_reflections": [],
                        },
                        "UNIT-2": {
                            "title": "Scientific Method",
                            "unit_order": 20,
                            "standards": [],
                            "shared_reflections": [],
                            "class_reflections": [],
                        },
                    },
                ),
                patch.object(module, "_fetch_material_map", return_value={}),
                patch.object(
                    module,
                    "_build_course_plan_timeline",
                    return_value={
                        "status": "ready",
                        "units": [
                            {"unit_plan": "UNIT-1", "is_current": 0},
                            {"unit_plan": "UNIT-2", "is_current": 1},
                        ],
                    },
                ),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(
                        name="COURSE-PLAN-1",
                        modified="2026-04-02 09:00:00",
                        summary="Shared course summary",
                        check_permission=lambda ptype: None,
                    ),
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={"course_name": "Biology", "course_group": "Science"},
                ),
                patch.object(
                    module,
                    "_fetch_academic_year_options_for_schools",
                    return_value={
                        "SCH-1": [
                            {"value": "2026-2027", "label": "2026-2027", "school": "SCH-1"},
                        ]
                    },
                ),
                patch.object(module, "_fetch_program_options_for_course", return_value=[]),
            ):
                payload = module._build_staff_course_plan_bundle("COURSE-PLAN-1")

        self.assertEqual(payload["resolved"]["unit_plan"], "UNIT-2")

    def test_build_staff_course_plan_bundle_passes_student_group_to_timeline(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={
                        "anchor_doctype": "Course Plan",
                        "anchor_name": "COURSE-PLAN-1",
                        "can_manage_resources": 1,
                    },
                ),
                patch.object(
                    module.planning,
                    "get_course_plan_row",
                    return_value={
                        "name": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "course": "COURSE-1",
                        "school": "SCH-1",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                    },
                ),
                patch.object(module, "_build_unit_lookup", return_value={}),
                patch.object(module, "_fetch_material_map", return_value={}),
                patch.object(module, "_fetch_course_quiz_question_banks", return_value=[]),
                patch.object(module, "_fetch_selected_quiz_question_bank", return_value=None),
                patch.object(module, "_fetch_academic_year_options_for_schools", return_value={"SCH-1": []}),
                patch.object(module, "_fetch_program_options_for_course", return_value=[]),
                patch.object(
                    module,
                    "_build_course_plan_timeline",
                    return_value={
                        "status": "blocked",
                        "reason": "missing_academic_year",
                        "message": "x",
                        "scope": {},
                        "terms": [],
                        "holidays": [],
                        "units": [],
                        "summary": {},
                    },
                ) as timeline_mock,
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(
                        name="COURSE-PLAN-1",
                        modified="2026-04-02 09:00:00",
                        summary="Shared course summary",
                        check_permission=lambda ptype: None,
                    ),
                ),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={"course_name": "Biology", "course_group": "Science"},
                ),
            ):
                module._build_staff_course_plan_bundle("COURSE-PLAN-1", student_group="GROUP-1")

        timeline_mock.assert_called_once()
        self.assertEqual(timeline_mock.call_args.kwargs["student_group"], "GROUP-1")

    def test_list_staff_course_plans_hides_rollover_drafts_for_non_coordinators_and_serializes_manage_flag(self):
        with _teaching_plans_module() as module:
            rows = [
                {
                    "name": "COURSE-PLAN-1",
                    "title": "Biology Plan",
                    "course": "COURSE-1",
                    "school": "SCH-1",
                    "academic_year": "2026-2027",
                    "cycle_label": "Semester 1",
                    "plan_status": "Active",
                    "rollover_source_course_plan": None,
                },
                {
                    "name": "COURSE-PLAN-2",
                    "title": "Biology Rollover Draft",
                    "course": "COURSE-2",
                    "school": "SCH-1",
                    "academic_year": "2026-2027",
                    "cycle_label": "Semester 2",
                    "plan_status": "Draft",
                    "rollover_source_course_plan": "COURSE-PLAN-1",
                },
                {
                    "name": "COURSE-PLAN-3",
                    "title": "Biology Working Draft",
                    "course": "COURSE-3",
                    "school": "SCH-1",
                    "academic_year": "2026-2027",
                    "cycle_label": "Semester 3",
                    "plan_status": "Draft",
                    "rollover_source_course_plan": None,
                },
            ]

            with (
                patch.object(module.frappe, "get_roles", return_value=["Academic Admin"]),
                patch.object(module.planning, "user_has_global_curriculum_access", return_value=True),
                patch.object(
                    module.planning,
                    "user_can_manage_course_curriculum",
                    side_effect=lambda user, course, roles=None: course == "COURSE-1",
                ),
                patch.object(module, "_fetch_academic_year_options_for_schools", return_value={}),
                patch.object(module.frappe, "get_list", return_value=rows),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {"name": "COURSE-1", "course_name": "Biology", "course_group": "Science"},
                        {"name": "COURSE-2", "course_name": "Biology B", "course_group": "Science"},
                        {"name": "COURSE-3", "course_name": "Biology C", "course_group": "Science"},
                    ],
                ),
            ):
                payload = module.list_staff_course_plans()

        self.assertEqual(len(payload["course_plans"]), 2)
        self.assertEqual(
            [row["name"] for row in payload["course_plans"]],
            ["COURSE-PLAN-1", "COURSE-PLAN-3"],
        )
        self.assertEqual(payload["course_plans"][0]["can_manage_resources"], 1)
        self.assertEqual(payload["course_plans"][1]["can_manage_resources"], 0)

    def test_list_staff_course_plans_includes_rollover_drafts_for_curriculum_coordinator(self):
        with _teaching_plans_module() as module:
            rows = [
                {
                    "name": "COURSE-PLAN-1",
                    "title": "Biology Plan",
                    "course": "COURSE-1",
                    "school": "SCH-1",
                    "academic_year": "2026-2027",
                    "cycle_label": "Semester 1",
                    "plan_status": "Active",
                    "rollover_source_course_plan": None,
                },
                {
                    "name": "COURSE-PLAN-2",
                    "title": "Biology Rollover Draft",
                    "course": "COURSE-2",
                    "school": "SCH-1",
                    "academic_year": "2026-2027",
                    "cycle_label": "Semester 2",
                    "plan_status": "Draft",
                    "rollover_source_course_plan": "COURSE-PLAN-1",
                },
            ]

            with (
                patch.object(module.frappe, "get_roles", return_value=["Curriculum Coordinator"]),
                patch.object(module.planning, "user_has_global_curriculum_access", return_value=True),
                patch.object(module.planning, "user_can_manage_course_curriculum", return_value=True),
                patch.object(module, "_fetch_academic_year_options_for_schools", return_value={}),
                patch.object(module.frappe, "get_list", return_value=rows),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {"name": "COURSE-1", "course_name": "Biology", "course_group": "Science"},
                        {"name": "COURSE-2", "course_name": "Biology B", "course_group": "Science"},
                    ],
                ),
            ):
                payload = module.list_staff_course_plans()

        self.assertEqual(
            [row["name"] for row in payload["course_plans"]],
            ["COURSE-PLAN-1", "COURSE-PLAN-2"],
        )

    def test_list_staff_course_plans_includes_creation_options_for_curriculum_coordinator(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(module.frappe, "get_roles", return_value=["Curriculum Coordinator"]),
                patch.object(module.planning, "get_curriculum_manageable_course_names", return_value=["COURSE-1"]),
                patch.object(
                    module,
                    "_fetch_academic_year_options_for_schools",
                    return_value={
                        "SCH-1": [
                            {"value": "2026-2027", "label": "2026-2027", "school": "SCH-1"},
                        ]
                    },
                ),
                patch.object(module.frappe, "get_list", return_value=[]),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {
                            "name": "COURSE-1",
                            "course_name": "Biology",
                            "course_group": "Science",
                            "school": "SCH-1",
                            "status": "Active",
                        }
                    ],
                ),
            ):
                payload = module.list_staff_course_plans()

        self.assertEqual(payload["access"]["can_create_course_plans"], 1)
        self.assertIsNone(payload["access"]["create_block_reason"])
        self.assertEqual(payload["course_options"][0]["course"], "COURSE-1")
        self.assertEqual(payload["course_options"][0]["course_name"], "Biology")
        self.assertEqual(payload["course_options"][0]["academic_year_options"][0]["value"], "2026-2027")

    def test_list_staff_course_plans_includes_creation_options_for_instructor_courses(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(module.frappe, "get_roles", return_value=["Instructor"]),
                patch.object(module.planning, "get_curriculum_manageable_course_names", return_value=["COURSE-1"]),
                patch.object(
                    module,
                    "_fetch_academic_year_options_for_schools",
                    return_value={
                        "SCH-1": [
                            {"value": "2026-2027", "label": "2026-2027", "school": "SCH-1"},
                        ]
                    },
                ),
                patch.object(module.frappe, "get_list", return_value=[]),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {
                            "name": "COURSE-1",
                            "course_name": "Biology",
                            "course_group": "Science",
                            "school": "SCH-1",
                            "status": "Active",
                        }
                    ],
                ),
            ):
                payload = module.list_staff_course_plans()

        self.assertEqual(payload["access"]["can_create_course_plans"], 1)
        self.assertEqual(payload["course_options"][0]["course"], "COURSE-1")
