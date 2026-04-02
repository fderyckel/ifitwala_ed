from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _teaching_plans_module():
    student_groups_api = ModuleType("ifitwala_ed.api.student_groups")
    student_groups_api.TRIAGE_ROLES = set()
    student_groups_api._instructor_group_names = lambda user: []

    file_access_api = ModuleType("ifitwala_ed.api.file_access")
    file_access_api.resolve_academic_file_open_url = lambda **kwargs: "/open/resource"

    materials_domain = ModuleType("ifitwala_ed.curriculum.materials")
    materials_domain.MATERIAL_TYPE_FILE = "File"
    materials_domain.MATERIAL_CLASS_OWNED_ANCHORS = {"Class Teaching Plan", "Class Session"}
    materials_domain.list_materials_for_anchors = lambda anchor_refs: {}
    materials_domain.resolve_anchor_context = lambda anchor_doctype, anchor_name: {
        "anchor_doctype": anchor_doctype,
        "anchor_name": anchor_name,
        "student_group": "GROUP-1",
    }
    materials_domain.resolve_material_origin = lambda anchor_doctype: "shared_in_class"
    materials_domain.create_reference_material = lambda **kwargs: (
        SimpleNamespace(name="MAT-1"),
        SimpleNamespace(name="MAT-PLC-1"),
    )
    materials_domain.create_file_material_record = lambda **kwargs: SimpleNamespace(name="MAT-1")
    materials_domain.create_material_placement = lambda **kwargs: SimpleNamespace(name="MAT-PLC-1")
    materials_domain.delete_anchor_material_placement = lambda *args, **kwargs: None
    materials_domain._get_coordinator_course_names = lambda user: []

    planning_domain = ModuleType("ifitwala_ed.curriculum.planning")
    planning_domain.normalize_text = lambda value: str(value or "").strip()
    planning_domain.normalize_long_text = lambda value: value
    planning_domain.normalize_flag = lambda value: 1 if str(value or "").strip() in {"1", "True", "true"} else 0
    planning_domain.user_has_global_curriculum_access = lambda user, roles=None: False
    planning_domain.get_instructor_course_names = lambda user: []
    planning_domain.get_coordinator_course_names = lambda user: []
    planning_domain.get_curriculum_manageable_course_names = lambda user, roles=None: []
    planning_domain.user_can_read_course_curriculum = lambda user, course, roles=None: False
    planning_domain.user_can_manage_course_curriculum = lambda user, course, roles=None: False
    planning_domain.assert_can_read_course_curriculum = lambda user, course, roles=None, action_label=None: None
    planning_domain.assert_can_manage_course_curriculum = lambda user, course, roles=None, action_label=None: None
    planning_domain.get_course_plan_row = lambda course_plan: {
        "name": course_plan,
        "title": course_plan,
        "course": "COURSE-1",
        "school": "SCH-1",
        "academic_year": "2026-2027",
    }
    planning_domain.get_student_group_row = lambda student_group: {"name": student_group, "course": "COURSE-1"}
    planning_domain.get_unit_plan_rows = lambda course_plan: []
    planning_domain.replace_session_activities = lambda doc, activities: None
    planning_domain.replace_lesson_activities = lambda doc, rows: doc.set("lesson_activities", rows)
    planning_domain.replace_unit_plan_standards = lambda doc, rows: doc.set("standards", rows)
    planning_domain.replace_unit_plan_reflections = lambda doc, rows, course_plan_row=None: doc.set("reflections", rows)
    planning_domain.next_lesson_order = lambda unit_plan: 10

    governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")
    governed_uploads.upload_supporting_material_file = lambda material: None

    quiz_service = ModuleType("ifitwala_ed.assessment.quiz_service")
    quiz_service.get_student_delivery_state_map = lambda **kwargs: {}

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.api.student_groups": student_groups_api,
            "ifitwala_ed.api.file_access": file_access_api,
            "ifitwala_ed.curriculum.materials": materials_domain,
            "ifitwala_ed.curriculum.planning": planning_domain,
            "ifitwala_ed.assessment.quiz_service": quiz_service,
            "ifitwala_ed.utilities.governed_uploads": governed_uploads,
        }
    ) as frappe:
        frappe.db.sql = lambda *args, **kwargs: []
        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.delete_doc = lambda *args, **kwargs: None
        frappe.get_all = lambda *args, **kwargs: []
        frappe.get_list = lambda *args, **kwargs: []
        yield import_fresh("ifitwala_ed.api.teaching_plans")


class TestTeachingPlansApi(TestCase):
    def test_fetch_assigned_work_includes_quiz_launch_state_for_students(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module.frappe.db,
                    "sql",
                    return_value=[
                        {
                            "task_delivery": "TDL-1",
                            "delivery_name": "TDL-1",
                            "task": "TASK-1",
                            "class_session": "SESSION-1",
                            "delivery_mode": "Assign Only",
                            "grading_mode": "None",
                            "available_from": None,
                            "due_date": "2026-04-10 09:00:00",
                            "lock_date": None,
                            "quiz_question_bank": "QBK-1",
                            "quiz_question_count": 10,
                            "quiz_time_limit_minutes": 20,
                            "quiz_max_attempts": 2,
                            "quiz_pass_percentage": 70,
                            "title": "Cells Checkpoint",
                            "task_type": "Quiz",
                            "unit_plan": "UNIT-1",
                            "lesson": "LESSON-1",
                        }
                    ],
                ),
                patch.object(module, "_fetch_material_map", return_value={}),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {
                            "task_delivery": "TDL-1",
                            "submission_status": "Submitted",
                            "grading_status": "Not Applicable",
                            "is_complete": 1,
                            "is_published": 0,
                        }
                    ],
                ),
                patch.object(
                    module.quiz_service,
                    "get_student_delivery_state_map",
                    return_value={
                        "TDL-1": {
                            "is_practice": 1,
                            "attempts_used": 1,
                            "max_attempts": 2,
                            "can_start": 0,
                            "can_continue": 1,
                            "can_retry": 0,
                            "latest_attempt": "QAT-1",
                            "status_label": "In Progress",
                            "score": None,
                            "percentage": None,
                            "passed": 0,
                            "pass_percentage": 70,
                            "time_limit_minutes": 20,
                        }
                    },
                ),
            ):
                payload = module._fetch_assigned_work(
                    "CLASS-PLAN-1",
                    audience="student",
                    student_name="STU-1",
                )

        self.assertEqual(payload[0]["task_delivery"], "TDL-1")
        self.assertEqual(payload[0]["submission_status"], "Submitted")
        self.assertEqual(payload[0]["quiz_state"]["can_continue"], 1)
        self.assertEqual(payload[0]["quiz_state"]["status_label"], "In Progress")

    def test_get_student_learning_space_includes_focus_and_next_actions(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(module, "_require_student_name", return_value="STU-1"),
                patch.object(module, "_assert_student_course_access", return_value=None),
                patch.object(
                    module,
                    "_resolve_student_group_options",
                    return_value=[{"student_group": "GROUP-1", "label": "Biology A"}],
                ),
                patch.object(
                    module,
                    "_resolve_student_plan",
                    return_value=(
                        "GROUP-1",
                        {
                            "name": "CLASS-PLAN-1",
                            "title": "Biology A",
                            "planning_status": "Active",
                        },
                    ),
                ),
                patch.object(module, "_assert_student_group_membership", return_value=None),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={
                        "name": "COURSE-1",
                        "course_name": "Biology",
                        "course_group": "Science",
                        "description": "Course description",
                        "course_image": "/files/biology.jpg",
                    },
                ),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(name="CLASS-PLAN-1", course_plan="COURSE-PLAN-1"),
                ),
                patch.object(module, "_build_unit_lookup", return_value={}),
                patch.object(
                    module,
                    "_serialize_backbone_units",
                    return_value=[
                        {
                            "unit_plan": "UNIT-1",
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "overview": "Shared unit overview",
                            "essential_understanding": "Systems work together.",
                            "content": "Cells",
                            "skills": "Observe",
                            "concepts": "Systems",
                            "standards": [],
                            "shared_resources": [],
                            "assigned_work": [],
                        }
                    ],
                ),
                patch.object(
                    module,
                    "_fetch_class_sessions",
                    return_value=[
                        {
                            "class_session": "SESSION-1",
                            "title": "Microscope evidence walk",
                            "unit_plan": "UNIT-1",
                            "session_status": "Planned",
                            "session_date": "2026-04-04",
                            "learning_goal": "Use microscope evidence to compare cells.",
                            "activities": [],
                            "resources": [],
                            "assigned_work": [],
                        }
                    ],
                ),
                patch.object(
                    module,
                    "_fetch_assigned_work",
                    return_value=[
                        {
                            "task_delivery": "TDL-1",
                            "task": "TASK-1",
                            "title": "Cell Structure Checkpoint",
                            "task_type": "Quiz",
                            "unit_plan": "UNIT-1",
                            "class_session": "SESSION-1",
                            "due_date": "2026-04-05 09:00:00",
                            "quiz_state": {
                                "can_continue": 1,
                                "status_label": "In Progress",
                            },
                            "materials": [],
                        }
                    ],
                ),
                patch.object(
                    module,
                    "_attach_resources_and_work",
                    return_value={
                        "shared_resources": [],
                        "class_resources": [],
                        "general_assigned_work": [
                            {
                                "task_delivery": "TDL-1",
                                "task": "TASK-1",
                                "title": "Cell Structure Checkpoint",
                                "task_type": "Quiz",
                                "unit_plan": "UNIT-1",
                                "class_session": "SESSION-1",
                                "due_date": "2026-04-05 09:00:00",
                                "quiz_state": {
                                    "can_continue": 1,
                                    "status_label": "In Progress",
                                },
                                "materials": [],
                            }
                        ],
                    },
                ),
                patch.object(module, "now_datetime", return_value=datetime(2026, 4, 2, 9, 0, 0)),
            ):
                payload = module.get_student_learning_space("COURSE-1", "GROUP-1")

        self.assertEqual(payload["learning"]["focus"]["current_unit"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["learning"]["focus"]["current_session"]["class_session"], "SESSION-1")
        self.assertEqual(payload["learning"]["selected_context"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["learning"]["selected_context"]["class_session"], "SESSION-1")
        self.assertEqual(payload["learning"]["next_actions"][0]["kind"], "quiz")
        self.assertIn("Cell Structure Checkpoint", payload["learning"]["next_actions"][0]["label"])

    def test_get_student_learning_space_falls_back_to_shared_course_plan_without_active_class(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(module, "_require_student_name", return_value="STU-1"),
                patch.object(module, "_assert_student_course_access", return_value=None),
                patch.object(module, "_resolve_student_group_options", return_value=[]),
                patch.object(
                    module.frappe.db,
                    "get_value",
                    return_value={
                        "name": "COURSE-1",
                        "course_name": "Biology",
                        "course_group": "Science",
                        "description": "Course description",
                        "course_image": "/files/biology.jpg",
                    },
                ),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[{"name": "COURSE-PLAN-1", "title": "Shared Biology Plan"}],
                ),
                patch.object(
                    module,
                    "_build_unit_lookup",
                    return_value={
                        "UNIT-1": {
                            "name": "UNIT-1",
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "program": "IB MYP",
                            "unit_code": "BIO-1",
                            "unit_status": "Published",
                            "version": "1",
                            "duration": "4 weeks",
                            "estimated_duration": "16 hours",
                            "overview": "Shared unit overview",
                            "essential_understanding": "Systems work together.",
                            "content": "Cells",
                            "skills": "Observe",
                            "concepts": "Systems",
                            "standards": [],
                        }
                    },
                ),
                patch.object(
                    module,
                    "_attach_resources_and_work",
                    return_value={
                        "shared_resources": [],
                        "class_resources": [],
                        "general_assigned_work": [],
                    },
                ),
                patch.object(module, "now_datetime", return_value=datetime(2026, 4, 2, 9, 0, 0)),
            ):
                payload = module.get_student_learning_space("COURSE-1")

        self.assertEqual(payload["teaching_plan"]["source"], "course_plan_fallback")
        self.assertEqual(payload["access"]["student_group_options"], [])
        self.assertIsNone(payload["access"]["resolved_student_group"])
        self.assertEqual(payload["access"]["course_plan"], "COURSE-PLAN-1")
        self.assertEqual(payload["curriculum"]["counts"]["units"], 1)
        self.assertIn("Showing the shared course plan", payload["message"])

    def test_build_unit_lookup_includes_shared_and_class_reflections_for_staff(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module.planning,
                    "get_unit_plan_rows",
                    return_value=[
                        {
                            "name": "UNIT-1",
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "overview": "Shared unit overview",
                            "essential_understanding": "Systems work together.",
                            "content": "Cells",
                            "skills": "Observe",
                            "concepts": "Systems",
                        }
                    ],
                ),
                patch.object(
                    module.frappe,
                    "get_all",
                    side_effect=[
                        [
                            {
                                "parent": "UNIT-1",
                                "standard_code": "STD-1",
                                "standard_description": "Explain how cells function.",
                                "coverage_level": "Introduced",
                            }
                        ],
                        [
                            {
                                "parent": "UNIT-1",
                                "academic_year": "2026-2027",
                                "prior_to_the_unit": "Shared reflection",
                            }
                        ],
                    ],
                ),
                patch.object(
                    module.frappe.db,
                    "sql",
                    return_value=[
                        {
                            "unit_plan": "UNIT-1",
                            "class_teaching_plan": "CLASS-PLAN-1",
                            "class_teaching_plan_title": "Biology A",
                            "student_group": "GROUP-1",
                            "academic_year": "2026-2027",
                            "student_group_name": "Biology A",
                            "student_group_abbreviation": "BIO-A",
                            "prior_to_the_unit": "Students needed microscope norms.",
                            "during_the_unit": "More modeling helped.",
                            "what_work_well": "Lab rotations",
                            "what_didnt_work_well": None,
                            "changes_suggestions": "Add more annotation examples.",
                        }
                    ],
                ),
            ):
                lookup = module._build_unit_lookup("COURSE-PLAN-1", audience="staff")

        self.assertEqual(lookup["UNIT-1"]["standards"][0]["standard_code"], "STD-1")
        self.assertEqual(lookup["UNIT-1"]["shared_reflections"][0]["prior_to_the_unit"], "Shared reflection")
        self.assertEqual(lookup["UNIT-1"]["class_reflections"][0]["class_label"], "Biology A")
        self.assertEqual(
            lookup["UNIT-1"]["class_reflections"][0]["changes_suggestions"],
            "Add more annotation examples.",
        )

    def test_serialize_backbone_units_hides_staff_only_reflections_from_students(self):
        with _teaching_plans_module() as module:
            with patch.object(
                module.frappe,
                "get_all",
                return_value=[
                    {
                        "unit_plan": "UNIT-1",
                        "unit_title": "Cells and Systems",
                        "unit_order": 10,
                        "governed_required": 1,
                        "pacing_status": "In Progress",
                        "teacher_focus": "Precision",
                        "pacing_note": "Slow down for lab setup",
                        "prior_to_the_unit": "Teacher-only",
                        "during_the_unit": "Teacher-only",
                        "what_work_well": "Teacher-only",
                        "what_didnt_work_well": "Teacher-only",
                        "changes_suggestions": "Teacher-only",
                    }
                ],
            ):
                payload = module._serialize_backbone_units(
                    "CLASS-PLAN-1",
                    {
                        "UNIT-1": {
                            "title": "Cells and Systems",
                            "unit_order": 10,
                            "overview": "Shared unit overview",
                            "essential_understanding": "Systems work together.",
                            "content": "Cells",
                            "skills": "Observe",
                            "concepts": "Systems",
                            "misconceptions": "Teacher-only misconception note",
                            "standards": [{"standard_code": "STD-1"}],
                            "shared_reflections": [{"prior_to_the_unit": "Teacher-only"}],
                            "class_reflections": [{"class_label": "Biology A"}],
                        }
                    },
                    audience="student",
                )

        self.assertEqual(payload[0]["overview"], "Shared unit overview")
        self.assertEqual(payload[0]["standards"][0]["standard_code"], "STD-1")
        self.assertNotIn("misconceptions", payload[0])
        self.assertNotIn("shared_reflections", payload[0])
        self.assertNotIn("class_reflections", payload[0])

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

    def test_fetch_class_sessions_hides_teacher_fields_for_students(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {
                            "name": "CLASS-SESSION-1",
                            "title": "Evidence walk",
                            "unit_plan": "UNIT-1",
                            "session_status": "Planned",
                            "session_date": None,
                            "sequence_index": 10,
                            "learning_goal": "Use evidence",
                            "teacher_note": "Teacher-only",
                        }
                    ],
                ),
                patch.object(
                    module.frappe.db,
                    "sql",
                    return_value=[
                        {
                            "parent": "CLASS-SESSION-1",
                            "title": "Observe",
                            "activity_type": "Discuss",
                            "estimated_minutes": 15,
                            "sequence_index": 10,
                            "student_direction": "Take notes.",
                            "teacher_prompt": "Push for precision.",
                            "resource_note": "Notebook needed.",
                            "idx": 1,
                        }
                    ],
                ),
            ):
                payload = module._fetch_class_sessions("CLASS-PLAN-1", audience="student")

        self.assertEqual(len(payload), 1)
        self.assertNotIn("teacher_note", payload[0])
        self.assertNotIn("teacher_prompt", payload[0]["activities"][0])
        self.assertEqual(payload[0]["activities"][0]["student_direction"], "Take notes.")

    def test_resolve_student_plan_reads_only_active_class_plans(self):
        with _teaching_plans_module() as module:
            with patch.object(
                module.frappe,
                "get_all",
                return_value=[
                    {
                        "name": "CLASS-PLAN-1",
                        "title": "Biology A",
                        "course_plan": "COURSE-PLAN-1",
                        "planning_status": "Active",
                        "team_note": None,
                    }
                ],
            ) as get_all:
                selected_group, class_plan_row = module._resolve_student_plan(
                    "COURSE-1",
                    [{"student_group": "GROUP-1", "label": "Biology A"}],
                    "GROUP-1",
                )

        self.assertEqual(selected_group, "GROUP-1")
        self.assertEqual(class_plan_row["name"], "CLASS-PLAN-1")
        self.assertEqual(get_all.call_args.kwargs["filters"]["planning_status"], "Active")

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

        self.assertEqual(payload["resolved"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["course_plan"]["can_manage_resources"], 1)
        self.assertEqual(payload["resources"]["course_plan_resources"][0]["title"], "Scope and sequence")
        self.assertEqual(payload["curriculum"]["units"][0]["shared_resources"][0]["title"], "Lab handout")

    def test_build_staff_course_plan_bundle_includes_lessons_and_quiz_bank_detail(self):
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
                    "_fetch_selected_unit_lessons",
                    return_value=[{"lesson": "LESSON-1", "title": "Microscope setup", "activities": []}],
                ),
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
                payload = module._build_staff_course_plan_bundle("COURSE-PLAN-1")

        self.assertEqual(payload["curriculum"]["selected_unit_lessons"][0]["lesson"], "LESSON-1")
        self.assertEqual(payload["assessment"]["quiz_question_banks"][0]["quiz_question_bank"], "QBK-1")
        self.assertEqual(payload["field_options"]["academic_years"][0]["value"], "2026-2027")
        self.assertEqual(payload["field_options"]["programs"][0]["value"], "MYP")
        self.assertEqual(
            payload["assessment"]["selected_quiz_question_bank"]["questions"][0]["quiz_question"],
            "QQ-1",
        )

    def test_list_staff_course_plans_serializes_manage_flag(self):
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
                },
                {
                    "name": "COURSE-PLAN-2",
                    "title": "Biology Plan B",
                    "course": "COURSE-2",
                    "school": "SCH-1",
                    "academic_year": "2026-2027",
                    "cycle_label": "Semester 2",
                    "plan_status": "Draft",
                },
            ]

            with (
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
                    ],
                ),
            ):
                payload = module.list_staff_course_plans()

        self.assertEqual(len(payload["course_plans"]), 2)
        self.assertEqual(payload["course_plans"][0]["can_manage_resources"], 1)
        self.assertEqual(payload["course_plans"][1]["can_manage_resources"], 0)

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

    def test_create_course_plan_creates_shared_plan_for_allowed_course(self):
        with _teaching_plans_module() as module:
            inserted = {"count": 0}

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
                    self.course = None
                    self.title = None
                    self.academic_year = None
                    self.cycle_label = None
                    self.plan_status = "Draft"
                    self.summary = None

                def insert(self, ignore_permissions=False):
                    inserted["count"] += 1
                    inserted["ignore_permissions"] = ignore_permissions

            doc = CoursePlanDoc()

            with (
                patch.object(module.frappe, "get_roles", return_value=["Instructor"]),
                patch.object(module.planning, "get_curriculum_manageable_course_names", return_value=["COURSE-1"]),
                patch.object(module, "_validate_course_plan_academic_year"),
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
                patch.object(module.frappe, "new_doc", return_value=doc),
            ):
                payload = module.create_course_plan(
                    {
                        "course": "COURSE-1",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "summary": "Shared scope and sequence",
                    }
                )

        self.assertEqual(doc.course, "COURSE-1")
        self.assertEqual(doc.title, "Biology Plan")
        self.assertEqual(doc.academic_year, "2026-2027")
        self.assertEqual(doc.cycle_label, "Semester 1")
        self.assertEqual(doc.summary, "Shared scope and sequence")
        self.assertEqual(inserted["count"], 1)
        self.assertEqual(payload["course_plan"], "COURSE-PLAN-1")
        self.assertEqual(payload["course"], "COURSE-1")

    def test_create_course_plan_rejects_users_without_shared_plan_permission(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.PermissionError):
                module.create_course_plan({"course": "COURSE-1"})

    def test_save_course_plan_updates_governed_fields(self):
        with _teaching_plans_module() as module:
            saved = {"count": 0}

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
                    self.course = "COURSE-1"
                    self.school = "SCH-1"
                    self.title = "Old title"
                    self.academic_year = None
                    self.cycle_label = None
                    self.plan_status = "Draft"
                    self.summary = None

                def check_permission(self, ptype):
                    self.checked = ptype

                def save(self, ignore_permissions=False):
                    saved["count"] += 1
                    saved["ignore_permissions"] = ignore_permissions

            doc = CoursePlanDoc()

            with (
                patch.object(module, "_validate_course_plan_academic_year"),
                patch.object(module.frappe, "get_doc", return_value=doc),
            ):
                payload = module.save_course_plan(
                    {
                        "course_plan": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "academic_year": "2026-2027",
                        "cycle_label": "Semester 1",
                        "plan_status": "Active",
                        "summary": "Shared scope and sequence",
                    }
                )

        self.assertEqual(doc.title, "Biology Plan")
        self.assertEqual(doc.plan_status, "Active")
        self.assertEqual(saved["count"], 1)
        self.assertEqual(payload["course_plan"], "COURSE-PLAN-1")

    def test_save_course_plan_rejects_academic_year_outside_course_school_scope(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.ValidationError):
                with (
                    patch.object(module, "_academic_year_scope_for_school", return_value=["SCH-1"]),
                    patch.object(
                        module.frappe.db,
                        "get_value",
                        return_value={"name": "2026-2027", "school": "SCH-OTHER"},
                    ),
                ):
                    module._validate_course_plan_academic_year(
                        course_school="SCH-1",
                        academic_year="2026-2027",
                    )

    def test_save_unit_plan_creates_new_unit_with_child_rows(self):
        with _teaching_plans_module() as module:
            inserted = {"count": 0}

            class FakeUnitDoc:
                def __init__(self):
                    self.name = "UNIT-PLAN-NEW"
                    self.course_plan = None
                    self.title = None
                    self.program = None
                    self.unit_code = None
                    self.unit_order = None
                    self.unit_status = "Draft"
                    self.version = None
                    self.duration = None
                    self.estimated_duration = None
                    self.is_published = 0
                    self.overview = None
                    self.essential_understanding = None
                    self.misconceptions = None
                    self.content = None
                    self.skills = None
                    self.concepts = None
                    self.standards = []
                    self.reflections = []

                def set(self, fieldname, value):
                    setattr(self, fieldname, value)

                def is_new(self):
                    return True

                def insert(self, ignore_permissions=False):
                    inserted["count"] += 1
                    inserted["ignore_permissions"] = ignore_permissions

            course_plan_doc = SimpleNamespace(check_permission=lambda ptype: None)
            unit_doc = FakeUnitDoc()

            def fake_get_doc(doctype, name):
                if doctype == "Course Plan":
                    return course_plan_doc
                raise AssertionError(f"Unexpected get_doc call: {doctype} {name}")

            with (
                patch.object(module, "_validate_course_program_link"),
                patch.object(module.frappe, "get_doc", side_effect=fake_get_doc),
                patch.object(module.frappe, "new_doc", return_value=unit_doc),
            ):
                payload = module.save_unit_plan(
                    {
                        "course_plan": "COURSE-PLAN-1",
                        "title": "Cells and Systems",
                        "unit_order": 10,
                        "is_published": 1,
                        "overview": "Shared unit overview",
                        "standards_json": [{"standard_code": "STD-1"}],
                        "reflections_json": [{"prior_to_the_unit": "Start with microscope norms."}],
                    }
                )

        self.assertEqual(unit_doc.course_plan, "COURSE-PLAN-1")
        self.assertEqual(unit_doc.title, "Cells and Systems")
        self.assertEqual(unit_doc.is_published, 1)
        self.assertEqual(unit_doc.standards, [{"standard_code": "STD-1"}])
        self.assertEqual(unit_doc.reflections, [{"prior_to_the_unit": "Start with microscope norms."}])
        self.assertEqual(inserted["count"], 1)
        self.assertEqual(payload["unit_plan"], "UNIT-PLAN-NEW")

    def test_validate_course_program_link_rejects_unlinked_program(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.ValidationError):
                with patch.object(
                    module.frappe.db,
                    "exists",
                    side_effect=lambda doctype, filters=None: doctype == "Program",
                ):
                    module._validate_course_program_link(course="COURSE-1", program="MYP")

    def test_save_lesson_outline_creates_lesson_with_activities(self):
        with _teaching_plans_module() as module:
            inserted = {"count": 0}

            class FakeLessonDoc:
                def __init__(self):
                    self.name = "LESSON-1"
                    self.unit_plan = None
                    self.course = None
                    self.title = None
                    self.lesson_type = None
                    self.lesson_order = None
                    self.is_published = 0
                    self.start_date = None
                    self.duration = None
                    self.lesson_activities = []

                def set(self, fieldname, value):
                    setattr(self, fieldname, value)

                def is_new(self):
                    return True

                def insert(self, ignore_permissions=False):
                    inserted["count"] += 1
                    inserted["ignore_permissions"] = ignore_permissions

            unit_doc = SimpleNamespace(
                name="UNIT-1",
                course="COURSE-1",
                check_permission=lambda ptype: None,
            )
            lesson_doc = FakeLessonDoc()

            def fake_get_doc(doctype, name):
                if doctype == "Unit Plan":
                    return unit_doc
                raise AssertionError(f"Unexpected get_doc call: {doctype} {name}")

            with (
                patch.object(module.frappe, "get_doc", side_effect=fake_get_doc),
                patch.object(module.frappe, "new_doc", return_value=lesson_doc),
            ):
                payload = module.save_lesson_outline(
                    {
                        "unit_plan": "UNIT-1",
                        "title": "Microscope setup",
                        "lesson_type": "Instruction",
                        "lesson_order": 20,
                        "is_published": 1,
                        "duration": 2,
                        "activities_json": [
                            {
                                "title": "Observe the slide",
                                "activity_type": "Discussion",
                                "lesson_activity_order": 10,
                            }
                        ],
                    }
                )

        self.assertEqual(lesson_doc.unit_plan, "UNIT-1")
        self.assertEqual(lesson_doc.course, "COURSE-1")
        self.assertEqual(lesson_doc.title, "Microscope setup")
        self.assertEqual(lesson_doc.lesson_activities[0]["title"], "Observe the slide")
        self.assertEqual(inserted["count"], 1)
        self.assertEqual(payload["lesson"], "LESSON-1")

    def test_remove_lesson_outline_deletes_unlinked_lesson(self):
        with _teaching_plans_module() as module:
            deleted = {"count": 0}

            class LessonDoc:
                def __init__(self):
                    self.unit_plan = "UNIT-1"

                def delete(self, ignore_permissions=False):
                    deleted["count"] += 1
                    deleted["ignore_permissions"] = ignore_permissions

            lesson_doc = LessonDoc()
            unit_doc = SimpleNamespace(course="COURSE-1", check_permission=lambda ptype: None)

            def fake_get_doc(doctype, name):
                if doctype == "Lesson":
                    return lesson_doc
                if doctype == "Unit Plan":
                    return unit_doc
                raise AssertionError(f"Unexpected get_doc call: {doctype} {name}")

            with (
                patch.object(module.frappe, "get_doc", side_effect=fake_get_doc),
                patch.object(module.frappe.db, "exists", return_value=False),
            ):
                payload = module.remove_lesson_outline("LESSON-1")

        self.assertEqual(payload["removed"], 1)
        self.assertEqual(deleted["count"], 1)

    def test_create_planning_reference_material_uses_class_owned_origin(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={"anchor_doctype": "Class Teaching Plan", "anchor_name": "CLASS-PLAN-1"},
                ),
                patch.object(
                    module.materials_domain,
                    "resolve_material_origin",
                    return_value="shared_in_class",
                ),
                patch.object(
                    module.materials_domain,
                    "create_reference_material",
                    return_value=(SimpleNamespace(name="MAT-1"), SimpleNamespace(name="MAT-PLC-1")),
                ) as create_reference_material,
                patch.object(
                    module,
                    "_reload_anchor_material",
                    return_value={"material": "MAT-1", "title": "Starter article"},
                ),
            ):
                payload = module.create_planning_reference_material(
                    {
                        "anchor_doctype": "Class Teaching Plan",
                        "anchor_name": "CLASS-PLAN-1",
                        "title": "Starter article",
                        "reference_url": "https://example.com/article",
                    }
                )

        self.assertEqual(payload["placement"], "MAT-PLC-1")
        create_reference_material.assert_called_once_with(
            anchor_doctype="Class Teaching Plan",
            anchor_name="CLASS-PLAN-1",
            title="Starter article",
            reference_url="https://example.com/article",
            description=None,
            modality=None,
            usage_role=None,
            placement_note=None,
            origin="shared_in_class",
        )

    def test_remove_planning_material_deletes_anchor_placement(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "_resolve_planning_resource_anchor",
                    return_value={"anchor_doctype": "Class Session", "anchor_name": "CLASS-SESSION-1"},
                ),
                patch.object(
                    module.materials_domain,
                    "delete_anchor_material_placement",
                ) as delete_placement,
            ):
                payload = module.remove_planning_material(
                    {
                        "anchor_doctype": "Class Session",
                        "anchor_name": "CLASS-SESSION-1",
                        "placement": "MAT-PLC-1",
                    }
                )

        self.assertEqual(payload["removed"], 1)
        delete_placement.assert_called_once_with(
            "MAT-PLC-1",
            anchor_doctype="Class Session",
            anchor_name="CLASS-SESSION-1",
        )
