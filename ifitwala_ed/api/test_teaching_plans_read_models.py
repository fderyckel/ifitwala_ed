from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.api.teaching_plans_test_support import _teaching_plans_module


class TestTeachingPlansReadModels(TestCase):
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
                            "requires_submission": 0,
                            "allow_late_submission": 0,
                            "available_from": None,
                            "due_date": "2026-04-10 09:00:00",
                            "lock_date": None,
                            "quiz_question_bank": "QBK-1",
                            "quiz_question_count": 10,
                            "quiz_time_limit_minutes": 20,
                            "quiz_max_attempts": 2,
                            "quiz_pass_percentage": 70,
                            "title": "Cells Checkpoint",
                            "instructions": "<p>Bring your notes.</p><script>alert(1)</script>",
                            "task_type": "Quiz",
                            "unit_plan": "UNIT-1",
                        }
                    ],
                ),
                patch.object(module, "_fetch_material_map", return_value={}),
                patch.object(module._read_models_impl, "sanitize_html", return_value="<p>Bring your notes.</p>"),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {
                            "name": "OUT-1",
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
        self.assertEqual(payload[0]["task_outcome"], "OUT-1")
        self.assertEqual(payload[0]["requires_submission"], 0)
        self.assertEqual(payload[0]["allow_late_submission"], 0)
        self.assertEqual(payload[0]["status_label"], "Completed")
        self.assertEqual(payload[0]["has_submission"], 1)
        self.assertEqual(payload[0]["is_done"], 1)
        self.assertEqual(payload[0]["is_actionable"], 1)
        self.assertEqual(payload[0]["quiz_state"]["can_continue"], 1)
        self.assertEqual(payload[0]["quiz_state"]["status_label"], "In Progress")
        self.assertEqual(payload[0]["instructions_html"], "<p>Bring your notes.</p>")

    def test_fetch_assigned_work_hides_internal_grading_status_labels_for_students(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module.frappe.db,
                    "sql",
                    return_value=[
                        {
                            "task_delivery": "TDL-2",
                            "delivery_name": "TDL-2",
                            "task": "TASK-2",
                            "class_session": "SESSION-1",
                            "delivery_mode": "Collect Work",
                            "grading_mode": "Rubric",
                            "requires_submission": 1,
                            "allow_late_submission": 1,
                            "available_from": "2026-04-05 10:00:00",
                            "due_date": "2026-04-06 09:00:00",
                            "lock_date": None,
                            "quiz_question_bank": None,
                            "quiz_question_count": None,
                            "quiz_time_limit_minutes": None,
                            "quiz_max_attempts": None,
                            "quiz_pass_percentage": None,
                            "title": "Cell comparison reflection",
                            "instructions": "Submit your reflection.",
                            "task_type": "Written Response",
                            "unit_plan": "UNIT-1",
                        }
                    ],
                ),
                patch.object(module, "_fetch_material_map", return_value={}),
                patch.object(module._read_models_impl, "sanitize_html", return_value="<p>Submit your reflection.</p>"),
                patch.object(
                    module.frappe,
                    "get_all",
                    return_value=[
                        {
                            "name": "OUT-2",
                            "task_delivery": "TDL-2",
                            "submission_status": "Not Submitted",
                            "grading_status": "Released",
                            "is_complete": 0,
                            "is_published": 1,
                        }
                    ],
                ),
                patch.object(module, "now_datetime", return_value=datetime(2026, 4, 5, 9, 0, 0)),
                patch.object(module.quiz_service, "get_student_delivery_state_map", return_value={}),
            ):
                payload = module._fetch_assigned_work(
                    "CLASS-PLAN-1",
                    audience="student",
                    student_name="STU-1",
                )

        self.assertEqual(payload[0]["status_label"], "Completed")

    def test_serialize_material_entry_uses_top_level_attachment_for_planning_file_material(self):
        with _teaching_plans_module() as module:
            with (
                patch.object(
                    module,
                    "resolve_academic_file_thumbnail_url",
                    return_value="/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?f=FILE-1",
                ) as resolve_thumbnail_url,
                patch.object(
                    module,
                    "resolve_academic_file_preview_url",
                    return_value="/api/method/ifitwala_ed.api.file_access.preview_academic_file?f=FILE-1",
                ) as resolve_preview_url,
                patch.object(
                    module,
                    "resolve_academic_file_open_url",
                    return_value="/api/method/ifitwala_ed.api.file_access.open_academic_file?f=FILE-1",
                ) as resolve_open_url,
            ):
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
                    },
                    thumbnail_ready_map={"FILE-1": True},
                    attachment_surface="planning.material",
                )

        resolve_thumbnail_url.assert_called_once_with(
            file_name="FILE-1",
            file_url="/private/files/lab.pdf",
            context_doctype="Material Placement",
            context_name="PLC-1",
            thumbnail_ready=True,
        )
        resolve_preview_url.assert_called_once_with(
            file_name="FILE-1",
            file_url="/private/files/lab.pdf",
            context_doctype="Material Placement",
            context_name="PLC-1",
        )
        resolve_open_url.assert_called_once_with(
            file_name="FILE-1",
            file_url="/private/files/lab.pdf",
            context_doctype="Material Placement",
            context_name="PLC-1",
        )
        self.assertNotIn("file_url", payload)
        self.assertNotIn("attachment_preview", payload)
        self.assertNotIn("thumbnail_url", payload)
        self.assertNotIn("preview_url", payload)
        self.assertNotIn("open_url", payload)
        self.assertEqual(payload["attachment"]["id"], "PLC-1")
        self.assertEqual(payload["attachment"]["surface"], "planning.material")
        self.assertEqual(payload["attachment"]["owner_doctype"], "Material Placement")
        self.assertEqual(payload["attachment"]["owner_name"], "PLC-1")
        self.assertEqual(payload["attachment"]["kind"], "pdf")
        self.assertEqual(
            payload["attachment"]["download_url"],
            "/api/method/ifitwala_ed.api.file_access.open_academic_file?f=FILE-1",
        )

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

    def test_attach_resources_wrapper_forwards_planning_attachment_surface(self):
        with _teaching_plans_module() as module:
            with patch.object(
                module._read_models_impl,
                "attach_resources_and_work",
                return_value={
                    "shared_resources": [],
                    "class_resources": [],
                    "general_assigned_work": [],
                },
            ) as attach_resources_and_work:
                payload = module._attach_resources_and_work(
                    units=[{"unit_plan": "UNIT-1", "sessions": []}],
                    course_plan="COURSE-PLAN-1",
                    class_teaching_plan="CLASS-PLAN-1",
                    assigned_work=[],
                    attachment_surface="planning.material",
                )

        self.assertEqual(payload["shared_resources"], [])
        attach_resources_and_work.assert_called_once_with(
            module,
            units=[{"unit_plan": "UNIT-1", "sessions": []}],
            course_plan="COURSE-PLAN-1",
            class_teaching_plan="CLASS-PLAN-1",
            assigned_work=[],
            attachment_surface="planning.material",
        )

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
