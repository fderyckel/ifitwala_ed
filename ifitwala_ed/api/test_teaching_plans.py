from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


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
    planning_domain.normalize_rich_text = lambda value, *, allow_headings_from="h2": (
        str(value or "").replace("<script>alert(1)</script>", "").strip() or None
    )
    planning_domain.normalize_flag = lambda value: 1 if str(value or "").strip() in {"1", "True", "true"} else 0
    planning_domain.normalize_record_modified = lambda value: str(value or "").strip()

    def _assert_record_modified_matches(*, expected_modified, current_modified, section_label):
        if expected_modified is None:
            return
        if str(expected_modified or "").strip() == str(current_modified or "").strip():
            return
        raise StubValidationError(f"{section_label} was updated by another user.")

    planning_domain.assert_record_modified_matches = _assert_record_modified_matches
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
    planning_domain.replace_unit_plan_standards = lambda doc, rows: doc.set("standards", rows)

    def _replace_unit_plan_reflections(doc, rows, course_plan_row=None):
        defaults = course_plan_row or {}
        doc.set(
            "reflections",
            [
                {
                    **(row or {}),
                    "academic_year": (row or {}).get("academic_year") or defaults.get("academic_year"),
                    "school": (row or {}).get("school") or defaults.get("school"),
                    "prior_to_the_unit": planning_domain.normalize_rich_text((row or {}).get("prior_to_the_unit")),
                    "during_the_unit": planning_domain.normalize_rich_text((row or {}).get("during_the_unit")),
                    "what_work_well": planning_domain.normalize_rich_text((row or {}).get("what_work_well")),
                    "what_didnt_work_well": planning_domain.normalize_rich_text(
                        (row or {}).get("what_didnt_work_well")
                    ),
                    "changes_suggestions": planning_domain.normalize_rich_text((row or {}).get("changes_suggestions")),
                }
                for row in rows or []
            ],
        )

    planning_domain.replace_unit_plan_reflections = _replace_unit_plan_reflections

    governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")
    governed_uploads.upload_supporting_material_file = lambda material: None

    quiz_service = ModuleType("ifitwala_ed.assessment.quiz_service")
    quiz_service.get_student_delivery_state_map = lambda **kwargs: {}

    school_settings_utils = ModuleType("ifitwala_ed.school_settings.school_settings_utils")
    school_settings_utils.resolve_school_calendars_for_window = lambda school, start_date, end_date: []

    schedule_utils = ModuleType("ifitwala_ed.schedule.schedule_utils")
    schedule_utils.get_calendar_holiday_set = lambda calendar_name: set()
    schedule_utils.get_weekend_days_for_calendar = lambda calendar_name: [0, 6]

    student_communications_api = ModuleType("ifitwala_ed.api.student_communications")
    student_communications_api.get_student_course_communication_summary = lambda *args, **kwargs: {
        "total_count": 0,
        "unread_count": 0,
        "high_priority_count": 0,
        "has_high_priority": 0,
        "latest_publish_at": None,
    }

    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.get_datetime = lambda value: (
        value
        if isinstance(value, datetime)
        else datetime.combine(value, datetime.min.time())
        if isinstance(value, date)
        else datetime.fromisoformat(str(value))
    )
    frappe_utils.getdate = lambda value: value if isinstance(value, date) else datetime.fromisoformat(str(value)).date()
    frappe_utils.now_datetime = lambda: "2026-04-07 10:30:00"
    frappe_utils.strip_html = lambda value: str(value or "").replace("<p>", "").replace("</p>", "")

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.api.student_groups": student_groups_api,
            "ifitwala_ed.api.file_access": file_access_api,
            "ifitwala_ed.api.student_communications": student_communications_api,
            "ifitwala_ed.curriculum.materials": materials_domain,
            "ifitwala_ed.curriculum.planning": planning_domain,
            "ifitwala_ed.assessment.quiz_service": quiz_service,
            "ifitwala_ed.school_settings.school_settings_utils": school_settings_utils,
            "ifitwala_ed.schedule.schedule_utils": schedule_utils,
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
                patch.object(
                    module,
                    "_fetch_student_learning_reflections",
                    return_value=[
                        {
                            "name": "REF-1",
                            "entry_date": "2026-04-02",
                            "entry_type": "Reflection",
                            "visibility": "Teacher",
                            "moderation_state": "Draft",
                            "body": "I can now compare plant and animal cells.",
                            "body_preview": "I can now compare plant and animal cells.",
                            "course": "COURSE-1",
                            "student_group": "GROUP-1",
                            "class_session": "SESSION-1",
                            "task_delivery": None,
                            "task_submission": None,
                        }
                    ],
                ),
                patch.object(module, "now_datetime", return_value=datetime(2026, 4, 2, 9, 0, 0)),
            ):
                payload = module.get_student_learning_space("COURSE-1", "GROUP-1")

        self.assertEqual(payload["learning"]["focus"]["current_unit"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["learning"]["focus"]["current_session"]["class_session"], "SESSION-1")
        self.assertEqual(payload["learning"]["selected_context"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["learning"]["selected_context"]["class_session"], "SESSION-1")
        self.assertEqual(payload["learning"]["reflection_entries"][0]["name"], "REF-1")
        self.assertEqual(payload["learning"]["reflection_entries"][0]["class_session"], "SESSION-1")
        self.assertEqual(payload["learning"]["next_actions"][0]["kind"], "quiz")
        self.assertIn("Cell Structure Checkpoint", payload["learning"]["next_actions"][0]["label"])
        self.assertEqual(
            payload["communications"]["course_updates_summary"],
            {
                "total_count": 0,
                "unread_count": 0,
                "high_priority_count": 0,
                "has_high_priority": 0,
                "latest_publish_at": None,
            },
        )

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

    def test_resolve_student_plan_rejects_spoofed_student_group(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.PermissionError):
                module._resolve_student_plan(
                    "COURSE-1",
                    [{"student_group": "GROUP-1", "label": "Biology A"}],
                    "GROUP-2",
                )

    def test_serialize_material_entry_uses_governed_open_url_for_file_material(self):
        with _teaching_plans_module() as module:
            with patch.object(
                module,
                "resolve_academic_file_open_url",
                return_value="/api/method/ifitwala_ed.api.file_access.open_academic_file?f=FILE-1",
            ) as resolve_open_url:
                payload = module._serialize_material_entry(
                    {
                        "material": "MAT-1",
                        "title": "Lab PDF",
                        "material_type": "File",
                        "file": "FILE-1",
                        "file_url": "/private/files/lab.pdf",
                        "file_name": "lab.pdf",
                        "placements": [
                            {
                                "placement": "PLC-1",
                                "origin": "shared_in_class",
                                "usage_role": "Core",
                                "placement_note": "Read before class",
                                "placement_order": 10,
                            }
                        ],
                    }
                )

        resolve_open_url.assert_called_once_with(
            file_name="FILE-1",
            file_url="/private/files/lab.pdf",
            context_doctype="Material Placement",
            context_name="PLC-1",
        )
        self.assertEqual(
            payload["open_url"],
            "/api/method/ifitwala_ed.api.file_access.open_academic_file?f=FILE-1",
        )
        self.assertNotIn("file_url", payload)

    def test_get_student_learning_space_logs_payload_metrics(self):
        with _teaching_plans_module() as module:
            module.frappe.db.query_count = 40
            logger = SimpleNamespace(info=Mock(), warning=Mock())

            def build_payload(*args, **kwargs):
                module.frappe.db.query_count = 47
                return {
                    "access": {
                        "resolved_student_group": "GROUP-1",
                    },
                    "teaching_plan": {
                        "source": "class_teaching_plan",
                    },
                    "curriculum": {
                        "counts": {
                            "units": 2,
                            "sessions": 12,
                            "assigned_work": 5,
                        },
                    },
                }

            with (
                patch.object(module, "_require_student_name", return_value="STU-1"),
                patch.object(module, "_build_student_learning_space_payload", side_effect=build_payload),
                patch.object(module.frappe, "logger", return_value=logger, create=True),
            ):
                payload = module.get_student_learning_space("COURSE-1", "GROUP-1")

        self.assertEqual(payload["curriculum"]["counts"]["units"], 2)
        logger.info.assert_called_once()
        logger.warning.assert_not_called()
        event = logger.info.call_args.args[0]
        self.assertEqual(event["event"], "student_learning_space_load")
        self.assertEqual(event["status"], "success")
        self.assertEqual(event["course_id"], "COURSE-1")
        self.assertEqual(event["student_group"], "GROUP-1")
        self.assertEqual(event["source"], "class_teaching_plan")
        self.assertEqual(event["unit_count"], 2)
        self.assertEqual(event["session_count"], 12)
        self.assertEqual(event["assigned_work_count"], 5)
        self.assertGreater(event["payload_bytes"], 0)
        self.assertEqual(event["db_query_count"], 7)

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
            ):
                payload = module._build_staff_course_plan_bundle("COURSE-PLAN-1")

        self.assertEqual(payload["assessment"]["quiz_question_banks"][0]["quiz_question_bank"], "QBK-1")
        self.assertEqual(payload["field_options"]["academic_years"][0]["value"], "2026-2027")
        self.assertEqual(payload["field_options"]["programs"][0]["value"], "MYP")
        self.assertEqual(
            payload["assessment"]["selected_quiz_question_bank"]["questions"][0]["quiz_question"],
            "QQ-1",
        )

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
        self.assertEqual(payload["units"][1]["schedule_state"], "unscheduled_duration")
        self.assertEqual(payload["units"][2]["schedule_state"], "blocked")

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

    def test_save_course_plan_sanitizes_summary_rich_text(self):
        with _teaching_plans_module() as module:

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
                    self.course = "COURSE-1"
                    self.school = "SCH-1"
                    self.modified = "2026-04-02 09:00:00"
                    self.summary = None

                def save(self, ignore_permissions=False):
                    return None

            doc = CoursePlanDoc()

            with (
                patch.object(module, "_validate_course_plan_academic_year"),
                patch.object(module.frappe, "get_doc", return_value=doc),
            ):
                module.save_course_plan(
                    {
                        "course_plan": "COURSE-PLAN-1",
                        "title": "Biology Plan",
                        "summary": "<h2>Overview</h2><script>alert(1)</script>",
                    }
                )

        self.assertEqual(doc.summary, "<h2>Overview</h2>")

    def test_save_course_plan_rejects_stale_expected_modified(self):
        with _teaching_plans_module() as module:

            class CoursePlanDoc:
                def __init__(self):
                    self.name = "COURSE-PLAN-1"
                    self.course = "COURSE-1"
                    self.school = "SCH-1"
                    self.modified = "2026-04-02 09:00:00"

                def save(self, ignore_permissions=False):
                    raise AssertionError("save() must not run after a stale expected_modified check.")

            with self.assertRaises(module.frappe.ValidationError):
                with (
                    patch.object(module, "_validate_course_plan_academic_year"),
                    patch.object(module.frappe, "get_doc", return_value=CoursePlanDoc()),
                ):
                    module.save_course_plan(
                        {
                            "course_plan": "COURSE-PLAN-1",
                            "title": "Biology Plan",
                            "expected_modified": "2026-04-02 08:00:00",
                        }
                    )

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
        self.assertEqual(
            unit_doc.reflections,
            [
                {
                    "academic_year": "2026-2027",
                    "school": "SCH-1",
                    "prior_to_the_unit": "Start with microscope norms.",
                    "during_the_unit": None,
                    "what_work_well": None,
                    "what_didnt_work_well": None,
                    "changes_suggestions": None,
                }
            ],
        )
        self.assertEqual(inserted["count"], 1)
        self.assertEqual(payload["unit_plan"], "UNIT-PLAN-NEW")

    def test_save_unit_plan_sanitizes_rich_text_fields_and_reflections(self):
        with _teaching_plans_module() as module:

            class FakeUnitDoc:
                def __init__(self):
                    self.name = "UNIT-PLAN-NEW"
                    self.course_plan = None
                    self.title = None
                    self.program = None
                    self.unit_order = None
                    self.is_published = 0
                    self.overview = None
                    self.reflections = []

                def set(self, fieldname, value):
                    setattr(self, fieldname, value)

                def is_new(self):
                    return True

                def insert(self, ignore_permissions=False):
                    return None

            unit_doc = FakeUnitDoc()

            with (
                patch.object(module, "_validate_course_program_link"),
                patch.object(
                    module.frappe,
                    "get_doc",
                    return_value=SimpleNamespace(check_permission=lambda ptype: None),
                ),
                patch.object(module.frappe, "new_doc", return_value=unit_doc),
            ):
                module.save_unit_plan(
                    {
                        "course_plan": "COURSE-PLAN-1",
                        "title": "Cells and Systems",
                        "overview": "<h2>Unit overview</h2><script>alert(1)</script>",
                        "reflections_json": [
                            {
                                "prior_to_the_unit": "<p>Start here</p><script>alert(1)</script>",
                            }
                        ],
                    }
                )

        self.assertEqual(unit_doc.overview, "<h2>Unit overview</h2>")
        self.assertEqual(unit_doc.reflections[0]["prior_to_the_unit"], "<p>Start here</p>")

    def test_save_unit_plan_rejects_stale_expected_modified(self):
        with _teaching_plans_module() as module:

            class FakeUnitDoc:
                def __init__(self):
                    self.name = "UNIT-PLAN-1"
                    self.course_plan = "COURSE-PLAN-1"
                    self.modified = "2026-04-02 09:00:00"

                def get_db_value(self, fieldname):
                    return None

                def save(self, ignore_permissions=False):
                    raise AssertionError("save() must not run after a stale expected_modified check.")

            def fake_get_doc(doctype, name):
                if doctype == "Unit Plan":
                    return FakeUnitDoc()
                if doctype == "Course Plan":
                    return SimpleNamespace(check_permission=lambda ptype: None)
                raise AssertionError(f"Unexpected get_doc call: {doctype} {name}")

            with self.assertRaises(module.frappe.ValidationError):
                with patch.object(module.frappe, "get_doc", side_effect=fake_get_doc):
                    module.save_unit_plan(
                        {
                            "unit_plan": "UNIT-PLAN-1",
                            "title": "Cells and Systems",
                            "expected_modified": "2026-04-02 08:00:00",
                        }
                    )

    def test_validate_course_program_link_rejects_unlinked_program(self):
        with _teaching_plans_module() as module:
            with self.assertRaises(module.frappe.ValidationError):
                with patch.object(
                    module.frappe.db,
                    "exists",
                    side_effect=lambda doctype, filters=None: doctype == "Program",
                ):
                    module._validate_course_program_link(course="COURSE-1", program="MYP")

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
