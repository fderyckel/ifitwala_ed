from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ifitwala_ed.api.teaching_plans_test_support import _teaching_plans_module


class TestTeachingPlansStudent(TestCase):
    def test_get_student_learning_space_includes_focus_and_next_actions(self):
        with _teaching_plans_module() as module:
            current_unit_resolver = Mock(
                return_value={
                    "unit_plan": "UNIT-1",
                    "unit": {"unit_plan": "UNIT-1", "title": "Cells and Systems"},
                    "source": "calendar",
                    "timeline": None,
                }
            )
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
                    return_value=SimpleNamespace(
                        name="CLASS-PLAN-1",
                        course_plan="COURSE-PLAN-1",
                        get=lambda fieldname, default=None: [] if fieldname == "units" else default,
                    ),
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
                        },
                        {
                            "task_delivery": "TDL-2",
                            "task": "TASK-2",
                            "task_outcome": "OUT-2",
                            "title": "Cell comparison reflection",
                            "task_type": "Written Response",
                            "unit_plan": "UNIT-1",
                            "class_session": "SESSION-1",
                            "requires_submission": 1,
                            "allow_late_submission": 1,
                            "submission_status": "Not Submitted",
                            "materials": [],
                        },
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
                            },
                            {
                                "task_delivery": "TDL-2",
                                "task": "TASK-2",
                                "task_outcome": "OUT-2",
                                "title": "Cell comparison reflection",
                                "task_type": "Written Response",
                                "unit_plan": "UNIT-1",
                                "class_session": "SESSION-1",
                                "requires_submission": 1,
                                "allow_late_submission": 1,
                                "submission_status": "Not Submitted",
                                "materials": [],
                            },
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
                patch.object(module, "_resolve_current_curriculum_unit", side_effect=current_unit_resolver),
                patch.object(module, "now_datetime", return_value=datetime(2026, 4, 2, 9, 0, 0)),
            ):
                payload = module.get_student_learning_space("COURSE-1", "GROUP-1")

        self.assertEqual(current_unit_resolver.call_args.kwargs["require_staff_access"], False)
        self.assertEqual(payload["learning"]["focus"]["current_unit"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["learning"]["focus"]["current_session"]["class_session"], "SESSION-1")
        self.assertEqual(payload["learning"]["selected_context"]["unit_plan"], "UNIT-1")
        self.assertEqual(payload["learning"]["selected_context"]["class_session"], "SESSION-1")
        self.assertEqual(payload["learning"]["selected_context"]["task_delivery"], "TDL-2")
        self.assertEqual(payload["curriculum"]["counts"]["assigned_work"], 2)
        self.assertEqual(payload["curriculum"]["counts"]["open_assigned_work"], 2)
        self.assertEqual(payload["curriculum"]["counts"]["completed_assigned_work"], 0)
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

    def test_student_next_actions_exclude_completed_non_quiz_work(self):
        with _teaching_plans_module() as module:
            units = [
                {
                    "unit_plan": "UNIT-1",
                    "title": "Cells and Systems",
                    "assigned_work": [
                        {
                            "task_delivery": "TDL-COMPLETE",
                            "title": "Completed notebook check",
                            "task_type": "Written Response",
                            "unit_plan": "UNIT-1",
                            "due_date": "2026-04-03 09:00:00",
                            "is_complete": 1,
                            "status_label": "Completed",
                        },
                        {
                            "task_delivery": "TDL-SUBMITTED",
                            "title": "Submitted reflection",
                            "task_type": "Written Response",
                            "unit_plan": "UNIT-1",
                            "due_date": "2026-04-04 09:00:00",
                            "submission_status": "Submitted",
                        },
                        {
                            "task_delivery": "TDL-OPEN",
                            "title": "Open reflection",
                            "task_type": "Written Response",
                            "unit_plan": "UNIT-1",
                            "due_date": "2026-04-05 09:00:00",
                        },
                        {
                            "task_delivery": "TDL-QUIZ-RETRY",
                            "title": "Retry quiz",
                            "task_type": "Quiz",
                            "unit_plan": "UNIT-1",
                            "due_date": "2026-04-06 09:00:00",
                            "submission_status": "Submitted",
                            "quiz_state": {"can_retry": 1, "status_label": "Submitted"},
                        },
                        {
                            "task_delivery": "TDL-QUIZ-DONE",
                            "title": "Finished quiz",
                            "task_type": "Quiz",
                            "unit_plan": "UNIT-1",
                            "due_date": "2026-04-07 09:00:00",
                            "is_complete": 1,
                            "quiz_state": {"status_label": "Passed"},
                        },
                    ],
                    "sessions": [],
                }
            ]

            with patch.object(module, "now_datetime", return_value=datetime(2026, 4, 2, 9, 0, 0)):
                actions = module._build_student_next_actions(units, [])
                navigation = module._build_student_unit_navigation(units, "UNIT-1")

        self.assertEqual([row.get("task_delivery") for row in actions], ["TDL-QUIZ-RETRY", "TDL-OPEN"])
        self.assertEqual(actions[0]["kind"], "quiz")
        self.assertEqual(actions[1]["kind"], "assigned_work")
        self.assertEqual(navigation[0]["assigned_work_count"], 5)
        self.assertEqual(navigation[0]["open_assigned_work_count"], 2)
        self.assertEqual(navigation[0]["completed_assigned_work_count"], 3)

    def test_student_selected_task_skips_completed_work(self):
        with _teaching_plans_module() as module:
            with patch.object(module, "now_datetime", return_value=datetime(2026, 4, 2, 9, 0, 0)):
                sections = module._build_student_learning_sections(
                    [
                        {
                            "unit_plan": "UNIT-1",
                            "title": "Cells and Systems",
                            "assigned_work": [
                                {
                                    "task_delivery": "TDL-COMPLETE",
                                    "title": "Completed notebook check",
                                    "task_type": "Written Response",
                                    "unit_plan": "UNIT-1",
                                    "is_complete": 1,
                                    "status_label": "Completed",
                                },
                                {
                                    "task_delivery": "TDL-OPEN",
                                    "title": "Open reflection",
                                    "task_type": "Written Response",
                                    "unit_plan": "UNIT-1",
                                },
                            ],
                            "sessions": [],
                        }
                    ],
                    [],
                    [],
                    "UNIT-1",
                    anchor_date=datetime(2026, 4, 2, 9, 0, 0),
                )

        self.assertEqual(sections["selected_context"]["task_delivery"], "TDL-OPEN")

    def test_get_student_learning_space_uses_resolved_current_unit_for_selected_context(self):
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
                    return_value=SimpleNamespace(
                        name="CLASS-PLAN-1",
                        course_plan="COURSE-PLAN-1",
                        get=lambda fieldname, default=None: [] if fieldname == "units" else default,
                    ),
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
                        },
                        {
                            "unit_plan": "UNIT-2",
                            "title": "Scientific Method",
                            "unit_order": 20,
                            "overview": "Shared unit overview",
                            "essential_understanding": "Evidence drives inquiry.",
                            "content": "Inquiry",
                            "skills": "Investigate",
                            "concepts": "Evidence",
                            "standards": [],
                            "shared_resources": [],
                            "assigned_work": [],
                        },
                    ],
                ),
                patch.object(
                    module,
                    "_fetch_class_sessions",
                    return_value=[
                        {
                            "class_session": "SESSION-2",
                            "title": "Hypothesis workshop",
                            "unit_plan": "UNIT-2",
                            "session_status": "Planned",
                            "session_date": "2026-04-10",
                            "learning_goal": "Plan a fair test.",
                            "activities": [],
                            "resources": [],
                            "assigned_work": [],
                        }
                    ],
                ),
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
                patch.object(module, "_fetch_student_learning_reflections", return_value=[]),
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
                patch.object(module, "now_datetime", return_value=datetime(2026, 4, 2, 9, 0, 0)),
            ):
                payload = module.get_student_learning_space("COURSE-1", "GROUP-1")

        self.assertEqual(payload["learning"]["selected_context"]["unit_plan"], "UNIT-2")
        self.assertEqual(payload["learning"]["focus"]["current_unit"]["unit_plan"], "UNIT-2")
        self.assertEqual(payload["learning"]["focus"]["current_session"]["class_session"], "SESSION-2")

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

    def test_assert_student_group_membership_uses_explicit_active_membership(self):
        with _teaching_plans_module() as module:
            captured = {}
            student_group = "25-26-G6-Math1/IIS 2025-2026"

            def _exists(doctype, filters):
                captured["doctype"] = doctype
                captured["filters"] = filters
                return "SGS-1"

            with patch.object(module.frappe.db, "exists", side_effect=_exists):
                module._assert_student_group_membership("STU-1", student_group)

        self.assertEqual(captured["doctype"], "Student Group Student")
        self.assertEqual(
            captured["filters"],
            {
                "parent": student_group,
                "parenttype": "Student Group",
                "student": "STU-1",
                "active": 1,
            },
        )

    def test_assert_student_group_membership_rejects_missing_or_inactive_rows(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(module.frappe.db, "exists", return_value=False),
                self.assertRaises(module.frappe.PermissionError),
            ):
                module._assert_student_group_membership("STU-1", "GROUP-1")

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
