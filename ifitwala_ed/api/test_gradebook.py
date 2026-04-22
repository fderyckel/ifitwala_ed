# ifitwala_ed/api/test_gradebook.py

from __future__ import annotations

import types
from unittest import TestCase
from urllib.parse import parse_qs, urlparse

from ifitwala_ed.tests.frappe_stubs import (
    StubPermissionError,
    StubValidationError,
    import_fresh,
    stubbed_frappe,
)


def _gradebook_stub_modules(
    task_contribution_service=None,
    task_feedback_service=None,
    task_feedback_comment_bank_service=None,
    task_feedback_thread_service=None,
    task_outcome_service=None,
):
    image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = (
        "profile_image_thumb",
        "profile_image_card",
        "profile_image_medium",
    )
    image_utils.apply_preferred_student_images = lambda rows: rows
    quiz_service = types.ModuleType("ifitwala_ed.assessment.quiz_service")
    quiz_service.MANUAL_TYPES = {"Essay"}
    quiz_service.refresh_attempt = lambda *args, **kwargs: {"attempt": {"name": args[0] if args else "QAT-1"}}
    feedback_service = task_feedback_service or types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
    if not hasattr(feedback_service, "build_feedback_workspace_payload"):
        feedback_service.build_feedback_workspace_payload = lambda outcome_id, submission_id, include_defaults=True: {
            "workspace_id": None,
            "task_outcome": outcome_id,
            "task_submission": submission_id,
            "submission_version": 1,
            "summary": {
                "overall": "",
                "strengths": "",
                "improvements": "",
                "next_steps": "",
            },
            "priorities": [],
            "items": [],
            "publication": {
                "feedback_visibility": "hidden",
                "grade_visibility": "hidden",
                "derived_from_legacy_outcome": True,
                "legacy_outcome_published": False,
                "legacy_published_on": None,
                "legacy_published_by": None,
            },
            "modified": None,
            "modified_by": None,
        }
    if not hasattr(feedback_service, "save_feedback_workspace_draft"):
        feedback_service.save_feedback_workspace_draft = lambda payload, actor=None: payload
    if not hasattr(feedback_service, "save_feedback_publication"):
        feedback_service.save_feedback_publication = lambda payload, actor=None: payload
    comment_bank_service = task_feedback_comment_bank_service or types.ModuleType(
        "ifitwala_ed.assessment.task_feedback_comment_bank_service"
    )
    if not hasattr(comment_bank_service, "build_comment_bank_payload"):
        comment_bank_service.build_comment_bank_payload = lambda outcome_id, actor=None: {
            "context": {
                "course": None,
                "task": None,
                "task_title": None,
                "criteria": [],
            },
            "entries": [],
        }
    if not hasattr(comment_bank_service, "save_comment_bank_entry"):
        comment_bank_service.save_comment_bank_entry = lambda payload, actor=None: {
            "context": {
                "course": None,
                "task": None,
                "task_title": None,
                "criteria": [],
            },
            "entries": [],
        }
    thread_service = task_feedback_thread_service or types.ModuleType(
        "ifitwala_ed.assessment.task_feedback_thread_service"
    )
    if not hasattr(thread_service, "build_feedback_thread_payloads"):
        thread_service.build_feedback_thread_payloads = lambda **kwargs: []
    if not hasattr(thread_service, "save_instructor_reply"):
        thread_service.save_instructor_reply = lambda payload, actor=None: {"thread": None}
    if not hasattr(thread_service, "save_instructor_thread_state"):
        thread_service.save_instructor_thread_state = lambda payload, actor=None: {"thread": None}
    file_access = types.ModuleType("ifitwala_ed.api.file_access")
    file_access.resolve_academic_file_open_url = (
        lambda *, file_name, file_url, context_doctype=None, context_name=None, **kwargs: (
            f"/api/method/ifitwala_ed.api.file_access.download_academic_file?file={file_name}&context_doctype={context_doctype}&context_name={context_name}"
            if file_name
            else file_url
        )
    )
    file_access.resolve_academic_file_preview_url = (
        lambda *, file_name, file_url, context_doctype=None, context_name=None, **kwargs: (
            f"/api/method/ifitwala_ed.api.file_access.preview_academic_file?file={file_name}&context_doctype={context_doctype}&context_name={context_name}"
            if file_name
            else file_url
        )
    )
    file_access.resolve_academic_file_thumbnail_url = (
        lambda *, file_name, file_url, context_doctype=None, context_name=None, **kwargs: (
            f"/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file={file_name}&context_doctype={context_doctype}&context_name={context_name}"
            if file_name
            else file_url
        )
    )
    file_access.get_drive_file_thumbnail_ready_map = lambda file_names: {
        file_name: False for file_name in (file_names or []) if file_name
    }

    return {
        "ifitwala_ed.api.file_access": file_access,
        "ifitwala_ed.assessment.quiz_service": quiz_service,
        "ifitwala_ed.assessment.task_contribution_service": task_contribution_service
        or types.ModuleType("ifitwala_ed.assessment.task_contribution_service"),
        "ifitwala_ed.assessment.task_feedback_comment_bank_service": comment_bank_service,
        "ifitwala_ed.assessment.task_feedback_service": feedback_service,
        "ifitwala_ed.assessment.task_feedback_thread_service": thread_service,
        "ifitwala_ed.assessment.task_outcome_service": task_outcome_service
        or types.ModuleType("ifitwala_ed.assessment.task_outcome_service"),
        "ifitwala_ed.assessment.task_submission_service": types.ModuleType(
            "ifitwala_ed.assessment.task_submission_service"
        ),
        "ifitwala_ed.utilities.image_utils": image_utils,
    }


def _import_fresh_gradebook():
    import_fresh("ifitwala_ed.api.gradebook_reads")
    import_fresh("ifitwala_ed.api.gradebook_writes")
    import_fresh("ifitwala_ed.api.gradebook_support")
    return import_fresh("ifitwala_ed.api.gradebook")


class TestGradebookApi(TestCase):
    def test_get_drawer_selects_requested_submission_version_and_serializes_preview_urls(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and name == "OUT-1":
                    return {
                        "name": "OUT-1",
                        "task_delivery": "TDL-1",
                        "student": "STU-1",
                        "grading_status": "Needs Review",
                        "procedural_status": "Submitted",
                        "has_submission": 1,
                        "has_new_submission": 1,
                        "is_complete": 0,
                        "is_published": 0,
                        "published_on": None,
                        "published_by": None,
                        "official_score": 8,
                        "official_grade": "B",
                        "official_grade_value": 8,
                        "official_feedback": "Review latest evidence",
                    }
                if doctype == "Task Delivery" and name == "TDL-1":
                    return {
                        "name": "TDL-1",
                        "task": "TASK-1",
                        "student_group": "GRP-1",
                        "due_date": "2026-04-03 10:00:00",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 1,
                        "max_points": 20,
                        "quiz_pass_percentage": None,
                        "rubric_version": None,
                        "rubric_scoring_strategy": None,
                    }
                if doctype == "Task" and name == "TASK-1":
                    return {"name": "TASK-1", "title": "Source Analysis", "task_type": "Assignment"}
                return None

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Submission":
                    self.assertNotIn("attachments", fields or [])
                    return [
                        {
                            "name": "TSU-2026-00002",
                            "version": 2,
                            "submitted_on": "2026-04-02 10:00:00",
                            "submitted_by": "student@example.com",
                            "is_late": 0,
                            "is_cloned": 0,
                            "cloned_from": "",
                            "submission_origin": "Student Upload",
                            "is_stub": 0,
                            "evidence_note": "Latest evidence",
                            "link_url": "",
                            "text_content": "Version 2",
                        },
                        {
                            "name": "TSU-2026-00001",
                            "version": 1,
                            "submitted_on": "2026-04-01 09:00:00",
                            "submitted_by": "student@example.com",
                            "is_late": 0,
                            "is_cloned": 0,
                            "cloned_from": "",
                            "submission_origin": "Student Upload",
                            "is_stub": 0,
                            "evidence_note": "Original evidence",
                            "link_url": "",
                            "text_content": "Version 1",
                        },
                    ]
                if doctype == "Task Contribution":
                    return []
                if doctype == "Attached Document":
                    self.assertEqual(filters.get("parent"), "TSU-2026-00001")
                    return [
                        {
                            "name": "ATT-OLD-1",
                            "file": "/private/files/submission-v1.pdf",
                            "external_url": "",
                            "description": "First upload",
                            "public": 0,
                            "file_name": "submission-v1.pdf",
                            "file_size": 512,
                        }
                    ]
                if doctype == "File":
                    self.assertEqual(filters.get("attached_to_name"), "TSU-2026-00001")
                    return [
                        {
                            "name": "FILE-SUB-0001",
                            "file_url": "/private/files/submission-v1.pdf",
                            "creation": "2026-04-01 09:00:00",
                        }
                    ]
                if doctype == "Drive File":
                    return [
                        {
                            "file": "FILE-SUB-0001",
                            "preview_status": "pending",
                            "current_version": "DFV-SUB-0001",
                        }
                    ]
                if doctype == "Drive File Version":
                    return [{"name": "DFV-SUB-0001", "mime_type": "application/pdf"}]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all

            module = _import_fresh_gradebook()
            module.gradebook_support._can_read_gradebook = lambda: True
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._get_outcome_criteria_map = lambda outcome_ids: {"OUT-1": []}
            module.gradebook_support._select_my_contribution = lambda contributions: None
            module.gradebook_support._get_student_display_map = lambda student_ids: {"STU-1": "Ada Lovelace"}
            module.gradebook_support._get_student_meta_map = lambda student_ids: {
                "STU-1": {
                    "name": "STU-1",
                    "student_id": "S-001",
                    "student_image": None,
                }
            }
            module.gradebook_support._build_delivery_criteria_payload = lambda delivery: []

            payload = module.get_drawer("OUT-1", version="1")

        self.assertEqual(payload["delivery"]["title"], "Source Analysis")
        self.assertEqual(payload["delivery"]["delivery_mode"], "Assess")
        self.assertEqual(payload["student"]["student_name"], "Ada Lovelace")
        self.assertEqual(payload["student"]["student_id"], "S-001")
        self.assertTrue(payload["outcome"]["has_submission"])
        self.assertTrue(payload["outcome"]["has_new_submission"])
        self.assertFalse(payload["outcome"]["is_published"])
        self.assertTrue(payload["allowed_actions"]["can_edit_marking"])
        self.assertEqual(payload["latest_submission"]["submission_id"], "TSU-2026-00002")
        self.assertFalse(payload["latest_submission"]["is_selected"])
        self.assertEqual(payload["selected_submission"]["submission_id"], "TSU-2026-00001")
        self.assertEqual(payload["selected_submission"]["version"], 1)
        self.assertEqual(payload["selected_submission"]["evidence_note"], "Original evidence")
        self.assertNotIn("submissions", payload)
        self.assertEqual(payload["feedback_workspace"]["task_submission"], "TSU-2026-00001")
        self.assertEqual(payload["feedback_workspace"]["publication"]["feedback_visibility"], "hidden")
        self.assertEqual(payload["comment_bank"]["entries"], [])
        self.assertEqual(payload["submission_versions"][0]["submission_id"], "TSU-2026-00001")
        self.assertTrue(payload["submission_versions"][0]["is_selected"])
        self.assertFalse(payload["submission_versions"][1]["is_selected"])

        attachment = payload["selected_submission"]["attachments"][0]
        self.assertEqual(attachment["preview_status"], "pending")
        self.assertEqual(attachment["mime_type"], "application/pdf")
        self.assertEqual(attachment["extension"], "pdf")
        self.assertEqual(attachment["attachment_preview"]["owner_doctype"], "Task Submission")
        self.assertEqual(attachment["attachment_preview"]["owner_name"], "TSU-2026-00001")
        self.assertEqual(attachment["attachment_preview"]["kind"], "pdf")
        self.assertFalse(attachment["attachment_preview"]["is_latest_version"])
        self.assertEqual(attachment["attachment_preview"]["version_label"], "Version 1")
        self.assertEqual(
            urlparse(attachment["open_url"]).path,
            "/api/method/ifitwala_ed.api.file_access.download_academic_file",
        )
        preview_parsed = urlparse(attachment["preview_url"])
        preview_query = parse_qs(preview_parsed.query)
        self.assertEqual(preview_parsed.path, "/api/method/ifitwala_ed.api.file_access.preview_academic_file")
        self.assertEqual((preview_query.get("file") or [None])[0], "FILE-SUB-0001")
        self.assertEqual((preview_query.get("context_name") or [None])[0], "TSU-2026-00001")
        self.assertEqual(payload["selected_submission"]["annotation_readiness"]["mode"], "reduced")
        self.assertEqual(
            payload["selected_submission"]["annotation_readiness"]["reason_code"],
            "pdf_preview_pending",
        )

    def test_save_feedback_draft_uses_named_feedback_service(self):
        saved_payloads = []

        feedback_service = types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
        feedback_service.build_feedback_workspace_payload = lambda *args, **kwargs: None
        feedback_service.save_feedback_workspace_draft = lambda payload, actor=None: (
            saved_payloads.append((payload, actor))
            or {
                "workspace_id": "TFW-1",
                "task_outcome": payload["outcome_id"],
                "task_submission": payload["submission_id"],
                "submission_version": 2,
                "summary": payload.get("summary") or {},
                "items": payload.get("items") or [],
                "publication": {
                    "feedback_visibility": "hidden",
                    "grade_visibility": "hidden",
                    "derived_from_legacy_outcome": False,
                    "legacy_outcome_published": False,
                    "legacy_published_on": None,
                    "legacy_published_by": None,
                },
                "modified": None,
                "modified_by": actor,
            }
        )
        feedback_service.save_feedback_publication = lambda payload, actor=None: payload

        with stubbed_frappe(extra_modules=_gradebook_stub_modules(task_feedback_service=feedback_service)) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and name == "OUT-1":
                    return {"task_delivery": "TDL-1"}
                if doctype == "Task Delivery" and name == "TDL-1":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "task": "TASK-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 1,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            response = module.save_feedback_draft(
                {
                    "outcome_id": "OUT-1",
                    "submission_id": "TSU-1",
                    "summary": {"overall": "Prioritise the thesis."},
                    "items": [
                        {
                            "kind": "page",
                            "page": 1,
                            "comment": "Start with a clearer claim.",
                            "intent": "next_step",
                            "workflow_state": "draft",
                            "anchor": {"kind": "page", "page": 1},
                        }
                    ],
                }
            )

        self.assertEqual(saved_payloads[0][0]["submission_id"], "TSU-1")
        self.assertEqual(saved_payloads[0][1], "unit.test@example.com")
        self.assertEqual(response["feedback_workspace"]["workspace_id"], "TFW-1")
        self.assertEqual(response["feedback_workspace"]["summary"]["overall"], "Prioritise the thesis.")

    def test_save_feedback_publication_uses_named_feedback_service(self):
        saved_payloads = []

        feedback_service = types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
        feedback_service.build_feedback_workspace_payload = lambda *args, **kwargs: None
        feedback_service.save_feedback_workspace_draft = lambda payload, actor=None: payload
        feedback_service.save_feedback_publication = lambda payload, actor=None: (
            saved_payloads.append((payload, actor))
            or {
                "workspace_id": "TFW-1",
                "task_outcome": payload["outcome_id"],
                "task_submission": payload["submission_id"],
                "submission_version": 2,
                "summary": {
                    "overall": "",
                    "strengths": "",
                    "improvements": "",
                    "next_steps": "",
                },
                "items": [],
                "publication": {
                    "feedback_visibility": payload["feedback_visibility"],
                    "grade_visibility": payload["grade_visibility"],
                    "derived_from_legacy_outcome": False,
                    "legacy_outcome_published": False,
                    "legacy_published_on": None,
                    "legacy_published_by": None,
                },
                "modified": None,
                "modified_by": actor,
            }
        )

        with stubbed_frappe(extra_modules=_gradebook_stub_modules(task_feedback_service=feedback_service)) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and name == "OUT-1":
                    return {"task_delivery": "TDL-1"}
                if doctype == "Task Delivery" and name == "TDL-1":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "task": "TASK-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 1,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            response = module.save_feedback_publication(
                {
                    "outcome_id": "OUT-1",
                    "submission_id": "TSU-1",
                    "feedback_visibility": "student",
                    "grade_visibility": "hidden",
                }
            )

        self.assertEqual(saved_payloads[0][0]["feedback_visibility"], "student")
        self.assertEqual(saved_payloads[0][0]["grade_visibility"], "hidden")
        self.assertEqual(saved_payloads[0][1], "unit.test@example.com")
        self.assertEqual(response["feedback_workspace"]["publication"]["feedback_visibility"], "student")

    def test_save_feedback_comment_bank_entry_uses_named_comment_bank_service(self):
        comment_bank_service = types.ModuleType("ifitwala_ed.assessment.task_feedback_comment_bank_service")
        saved_payloads = []
        comment_bank_service.build_comment_bank_payload = lambda outcome_id, actor=None: {"context": {}, "entries": []}
        comment_bank_service.save_comment_bank_entry = lambda payload, actor=None: (
            saved_payloads.append((payload, actor))
            or {
                "context": {
                    "course": "CRS-1",
                    "task": "TASK-1",
                    "task_title": "Essay",
                    "criteria": [],
                },
                "entries": [
                    {
                        "id": "BANK-1",
                        "label": "Use evidence",
                        "body": "Use a stronger quotation here.",
                        "intent": "issue",
                        "scope_mode": "task",
                        "course": "CRS-1",
                        "task": "TASK-1",
                        "assessment_criteria": None,
                        "assessment_criteria_label": None,
                        "match_reasons": ["task"],
                        "match_score": 4,
                    }
                ],
            }
        )

        with stubbed_frappe(
            extra_modules=_gradebook_stub_modules(task_feedback_comment_bank_service=comment_bank_service)
        ) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and name == "OUT-1":
                    return {"task_delivery": "TDL-1"}
                if doctype == "Task Delivery" and name == "TDL-1":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "task": "TASK-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Criteria",
                        "allow_feedback": 1,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            response = module.save_feedback_comment_bank_entry(
                {
                    "outcome_id": "OUT-1",
                    "body": "Use a stronger quotation here.",
                    "feedback_intent": "issue",
                    "scope_mode": "task",
                }
            )

        self.assertEqual(saved_payloads[0][0]["outcome_id"], "OUT-1")
        self.assertEqual(saved_payloads[0][1], "unit.test@example.com")
        self.assertEqual(response["comment_bank"]["entries"][0]["scope_mode"], "task")

    def test_submit_contribution_uses_named_service_and_resolves_submission(self):
        submitted_payloads = []

        task_contribution_service = types.ModuleType("ifitwala_ed.assessment.task_contribution_service")
        task_contribution_service.submit_contribution = lambda payload, contributor=None: (
            submitted_payloads.append((payload, contributor))
            or {
                "contribution": "TCO-1",
                "status": "Submitted",
                "task_outcome": payload.get("task_outcome"),
                "task_submission": payload.get("task_submission"),
                "outcome_update": {"outcome": payload.get("task_outcome"), "grading_status": "Finalized"},
            }
        )

        with stubbed_frappe(extra_modules=_gradebook_stub_modules(task_contribution_service=task_contribution_service)):
            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._resolve_or_create_stub_submission_id = lambda outcome_id, data: "SUB-1"

            payload = module.submit_contribution(
                task_outcome="OUT-1",
                score=12,
                feedback="Strong evidence.",
            )

        self.assertEqual(
            submitted_payloads,
            [
                (
                    {
                        "task_outcome": "OUT-1",
                        "score": 12,
                        "feedback": "Strong evidence.",
                        "task_submission": "SUB-1",
                    },
                    "unit.test@example.com",
                )
            ],
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["task_submission"], "SUB-1")
        self.assertEqual(payload["outcome_update"]["grading_status"], "Finalized")

    def test_moderator_action_requires_adminish_role(self):
        task_contribution_service = types.ModuleType("ifitwala_ed.assessment.task_contribution_service")
        task_contribution_service.apply_moderator_action = lambda payload, contributor=None: {
            "contribution": "TCO-MOD-1",
            "status": "Submitted",
            "task_outcome": payload.get("task_outcome"),
            "task_submission": payload.get("task_submission"),
            "outcome_update": {"outcome": payload.get("task_outcome"), "grading_status": "Moderated"},
        }

        with stubbed_frappe(extra_modules=_gradebook_stub_modules(task_contribution_service=task_contribution_service)):
            module = _import_fresh_gradebook()
            module.gradebook_support._is_academic_adminish = lambda: False

            with self.assertRaises(StubPermissionError):
                module.moderator_action(task_outcome="OUT-1", action="Approve")

    def test_moderator_action_uses_named_service_and_preserves_action(self):
        moderation_payloads = []

        task_contribution_service = types.ModuleType("ifitwala_ed.assessment.task_contribution_service")
        task_contribution_service.apply_moderator_action = lambda payload, contributor=None: (
            moderation_payloads.append((payload, contributor))
            or {
                "contribution": "TCO-MOD-1",
                "status": "Submitted",
                "task_outcome": payload.get("task_outcome"),
                "task_submission": payload.get("task_submission"),
                "outcome_update": {"outcome": payload.get("task_outcome"), "grading_status": "Moderated"},
            }
        )

        with stubbed_frappe(extra_modules=_gradebook_stub_modules(task_contribution_service=task_contribution_service)):
            module = _import_fresh_gradebook()
            module.gradebook_support._is_academic_adminish = lambda: True
            module.gradebook_support._resolve_or_create_stub_submission_id = lambda outcome_id, data: "SUB-MOD-1"

            payload = module.moderator_action(
                task_outcome="OUT-1",
                action="Adjust",
                score=14,
                feedback="Adjusted after review.",
            )

        self.assertEqual(
            moderation_payloads,
            [
                (
                    {
                        "task_outcome": "OUT-1",
                        "action": "Adjust",
                        "score": 14,
                        "feedback": "Adjusted after review.",
                        "task_submission": "SUB-MOD-1",
                    },
                    "unit.test@example.com",
                )
            ],
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["task_submission"], "SUB-MOD-1")
        self.assertEqual(payload["outcome_update"]["grading_status"], "Moderated")

    def test_get_task_gradebook_includes_submission_status_for_evidence_inbox_routing(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Delivery" and name == "TDL-1":
                    return {
                        "name": "TDL-1",
                        "task": "TASK-1",
                        "student_group": "GRP-1",
                        "due_date": "2026-04-03 10:00:00",
                        "delivery_mode": "Collect Work",
                        "grading_mode": "None",
                        "allow_feedback": 1,
                        "max_points": None,
                        "rubric_version": None,
                        "rubric_scoring_strategy": None,
                    }
                if doctype == "Task" and name == "TASK-1":
                    return {"name": "TASK-1", "title": "Science Journal", "task_type": "Assignment"}
                return None

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Outcome":
                    return [
                        {
                            "name": "OUT-1",
                            "student": "STU-1",
                            "grading_status": "Not Started",
                            "procedural_status": "Submitted",
                            "submission_status": "Late",
                            "has_submission": 1,
                            "has_new_submission": 1,
                            "is_complete": 0,
                            "official_score": None,
                            "official_feedback": None,
                            "is_published": 0,
                            "modified": "2026-04-18 10:10:00",
                        }
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all

            module = _import_fresh_gradebook()
            module.gradebook_support._can_read_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None
            module.gradebook_support._get_student_display_map = lambda student_ids: {"STU-1": "Ada Lovelace"}
            module.gradebook_support._get_student_meta_map = lambda student_ids: {
                "STU-1": {"name": "STU-1", "student_id": "S-001", "student_image": None}
            }
            module.gradebook_support._build_delivery_criteria_payload = lambda delivery: []
            module.gradebook_support._get_outcome_criteria_rows = lambda outcome_ids: {}

            payload = module.get_task_gradebook("TDL-1")

        self.assertEqual(payload["task"]["delivery_type"], "Collect Work")
        self.assertEqual(payload["students"][0]["submission_status"], "Late")
        self.assertEqual(payload["students"][0]["has_new_submission"], 1)

    def test_get_task_quiz_manual_review_groups_manual_rows_by_question(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "task": "TASK-QUIZ-1",
                        "student_group": "GRP-1",
                        "due_date": "2026-04-08 10:00:00",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 0,
                        "max_points": 4,
                        "rubric_version": None,
                        "rubric_scoring_strategy": None,
                        "quiz_pass_percentage": 75,
                    }
                if doctype == "Task":
                    return {"name": "TASK-QUIZ-1", "title": "Unit Reflection Quiz", "task_type": "Quiz"}
                return None

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Outcome":
                    return [
                        {"name": "OUT-1", "student": "STU-1", "grading_status": "Needs Review"},
                        {"name": "OUT-2", "student": "STU-2", "grading_status": "Finalized"},
                    ]
                if doctype == "Quiz Attempt":
                    return [
                        {
                            "name": "QAT-1",
                            "task_outcome": "OUT-1",
                            "student": "STU-1",
                            "attempt_number": 1,
                            "status": "Needs Review",
                            "submitted_on": "2026-04-08 10:15:00",
                            "score": None,
                            "percentage": None,
                            "passed": 0,
                            "requires_manual_review": 1,
                        },
                        {
                            "name": "QAT-2",
                            "task_outcome": "OUT-2",
                            "student": "STU-2",
                            "attempt_number": 1,
                            "status": "Submitted",
                            "submitted_on": "2026-04-08 10:25:00",
                            "score": 4,
                            "percentage": 100,
                            "passed": 1,
                            "requires_manual_review": 0,
                        },
                    ]
                if doctype == "Quiz Attempt Item":
                    return [
                        {
                            "name": "QAI-1",
                            "quiz_attempt": "QAT-1",
                            "quiz_question": "QQ-1",
                            "position": 1,
                            "question_type": "Essay",
                            "prompt_html": "<p>Explain your reasoning.</p>",
                            "option_payload": None,
                            "response_text": "Student one response",
                            "response_payload": None,
                            "awarded_score": None,
                            "requires_manual_grading": 1,
                        },
                        {
                            "name": "QAI-2",
                            "quiz_attempt": "QAT-2",
                            "quiz_question": "QQ-1",
                            "position": 1,
                            "question_type": "Essay",
                            "prompt_html": "<p>Explain your reasoning.</p>",
                            "option_payload": None,
                            "response_text": "Student two response",
                            "response_payload": None,
                            "awarded_score": 1,
                            "requires_manual_grading": 0,
                        },
                    ]
                if doctype == "Quiz Question":
                    return [{"name": "QQ-1", "title": "Explain the pattern"}]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all

            module = _import_fresh_gradebook()
            module.gradebook_support._can_read_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None
            module.gradebook_support._get_student_display_map = lambda student_ids: {
                "STU-1": "Ada Lovelace",
                "STU-2": "Grace Hopper",
            }
            module.gradebook_support._get_student_meta_map = lambda student_ids: {
                "STU-1": {"name": "STU-1", "student_id": "S-001", "student_image": None},
                "STU-2": {"name": "STU-2", "student_id": "S-002", "student_image": None},
            }

            payload = module.get_task_quiz_manual_review("TDL-1", view_mode="question")

        self.assertEqual(payload["task"]["title"], "Unit Reflection Quiz")
        self.assertEqual(payload["summary"]["manual_item_count"], 2)
        self.assertEqual(payload["summary"]["pending_item_count"], 1)
        self.assertEqual(payload["view_mode"], "question")
        self.assertEqual(payload["selected_question"], {"quiz_question": "QQ-1", "title": "Explain the pattern"})
        self.assertEqual([row["student_name"] for row in payload["rows"]], ["Ada Lovelace", "Grace Hopper"])
        self.assertEqual(payload["rows"][0]["requires_manual_grading"], 1)
        self.assertEqual(payload["rows"][1]["awarded_score"], 1.0)

    def test_save_task_quiz_manual_review_updates_items_and_refreshes_attempts(self):
        set_value_calls = []
        refresh_calls = []
        modules = _gradebook_stub_modules()
        modules["ifitwala_ed.assessment.quiz_service"].refresh_attempt = lambda attempt_id, **kwargs: (
            refresh_calls.append((attempt_id, kwargs)) or {"attempt": {"name": attempt_id}}
        )

        with stubbed_frappe(extra_modules=modules) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "task": "TASK-QUIZ-1",
                        "student_group": "GRP-1",
                        "due_date": "2026-04-08 10:00:00",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 0,
                        "max_points": 4,
                        "rubric_version": None,
                        "rubric_scoring_strategy": None,
                    }
                if doctype == "Task":
                    return {"name": "TASK-QUIZ-1", "title": "Unit Reflection Quiz", "task_type": "Quiz"}
                return None

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Quiz Attempt Item":
                    return [
                        {"name": "QAI-1", "quiz_attempt": "QAT-1", "question_type": "Essay"},
                        {"name": "QAI-2", "quiz_attempt": "QAT-2", "question_type": "Essay"},
                    ]
                if doctype == "Quiz Attempt":
                    return [
                        {
                            "name": "QAT-1",
                            "task_delivery": "TDL-1",
                            "student": "STU-1",
                            "status": "Needs Review",
                        },
                        {
                            "name": "QAT-2",
                            "task_delivery": "TDL-1",
                            "student": "STU-2",
                            "status": "Submitted",
                        },
                    ]
                return []

            frappe.db.get_value = fake_get_value
            frappe.get_all = fake_get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: set_value_calls.append(
                (doctype, name, values, update_modified)
            )

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            payload = module.save_task_quiz_manual_review(
                "TDL-1",
                grades=[
                    {"item_id": "QAI-1", "awarded_score": 1},
                    {"item_id": "QAI-2", "awarded_score": 0.5},
                ],
            )

        self.assertEqual(
            set_value_calls,
            [
                ("Quiz Attempt Item", "QAI-1", {"awarded_score": 1.0}, True),
                ("Quiz Attempt Item", "QAI-2", {"awarded_score": 0.5}, True),
            ],
        )
        self.assertEqual(
            refresh_calls,
            [
                (
                    "QAT-1",
                    {"user": "unit.test@example.com", "mark_submitted": True, "student": "STU-1"},
                ),
                (
                    "QAT-2",
                    {"user": "unit.test@example.com", "mark_submitted": True, "student": "STU-2"},
                ),
            ],
        )
        self.assertEqual(payload, {"updated_item_count": 2, "updated_attempt_count": 2})

    def test_fetch_group_tasks_exposes_grading_mode_and_comment_flag(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0):
                if doctype == "Task Delivery":
                    return [
                        {
                            "name": "TDL-0001",
                            "task": "TASK-1",
                            "due_date": "2026-04-03 10:00:00",
                            "delivery_mode": "Assess",
                            "grading_mode": "Criteria",
                            "allow_feedback": 1,
                            "max_points": None,
                            "rubric_scoring_strategy": "Separate Criteria",
                        }
                    ]
                if doctype == "Task":
                    return [{"name": "TASK-1", "title": "Rubric reflection", "task_type": "Assignment"}]
                return []

            frappe.get_all = fake_get_all

            module = _import_fresh_gradebook()
            module.gradebook_support._can_read_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            payload = module.fetch_group_tasks("GRP-1")

        self.assertEqual(
            payload,
            {
                "tasks": [
                    {
                        "name": "TDL-0001",
                        "title": "Rubric reflection",
                        "due_date": "2026-04-03 10:00:00",
                        "status": None,
                        "grading_mode": "Criteria",
                        "allow_feedback": 1,
                        "rubric_scoring_strategy": "Separate Criteria",
                        "points": 0,
                        "binary": 0,
                        "criteria": 1,
                        "observations": 0,
                        "max_points": None,
                        "task_type": "Assignment",
                        "delivery_type": "Assess",
                    }
                ]
            },
        )

    def test_get_grid_returns_bounded_overview_payload_for_selected_group(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Delivery":
                    return [
                        {
                            "name": "TDL-0002",
                            "task": "TASK-2",
                            "grading_mode": "Points",
                            "rubric_scoring_strategy": None,
                            "due_date": "2026-04-04 10:00:00",
                            "delivery_mode": "Assess",
                            "allow_feedback": 0,
                            "max_points": 20,
                        },
                        {
                            "name": "TDL-0001",
                            "task": "TASK-1",
                            "grading_mode": "Criteria",
                            "rubric_scoring_strategy": "Separate Criteria",
                            "due_date": "2026-04-03 10:00:00",
                            "delivery_mode": "Assess",
                            "allow_feedback": 1,
                            "max_points": None,
                        },
                    ]
                if doctype == "Task":
                    return [
                        {"name": "TASK-1", "title": "Rubric reflection", "task_type": "Assignment"},
                        {"name": "TASK-2", "title": "Quiz score", "task_type": "Quiz"},
                    ]
                if doctype == "Task Outcome":
                    return [
                        {
                            "name": "OUT-1",
                            "task_delivery": "TDL-0001",
                            "student": "STU-1",
                            "grading_status": "Needs Review",
                            "procedural_status": None,
                            "has_submission": 1,
                            "has_new_submission": 1,
                            "official_score": None,
                            "official_grade": None,
                            "official_grade_value": None,
                            "official_feedback": "Great detail.",
                            "is_complete": 0,
                            "is_published": 0,
                        },
                        {
                            "name": "OUT-2",
                            "task_delivery": "TDL-0002",
                            "student": "STU-1",
                            "grading_status": "Released",
                            "procedural_status": None,
                            "has_submission": 1,
                            "has_new_submission": 0,
                            "official_score": 18,
                            "official_grade": "A",
                            "official_grade_value": "A",
                            "official_feedback": None,
                            "is_complete": 0,
                            "is_published": 1,
                        },
                    ]
                if doctype == "Task Outcome Criterion":
                    return [
                        {
                            "parent": "OUT-1",
                            "assessment_criteria": "CRIT-1",
                            "level": "Secure",
                            "level_points": 4,
                        }
                    ]
                return []

            frappe.get_all = fake_get_all

            module = _import_fresh_gradebook()
            module.gradebook_support._can_read_gradebook = lambda: True
            module.gradebook_support._resolve_gradebook_scope = lambda school, academic_year, course: {
                "courses": [course] if course else [],
                "student_groups": ["GRP-1"],
            }
            module.gradebook_support._assert_group_access = lambda student_group: None
            module.gradebook_support._get_student_display_map = lambda student_ids: {"STU-1": "Ada Lovelace"}
            module.gradebook_support._get_student_meta_map = lambda student_ids: {
                "STU-1": {"student_id": "S-001", "student_image": None}
            }

            payload = module.get_grid(
                {
                    "school": "SCH-1",
                    "academic_year": "2025-2026",
                    "student_group": "GRP-1",
                    "limit": 2,
                }
            )

        self.assertEqual(
            payload["deliveries"],
            [
                {
                    "delivery_id": "TDL-0001",
                    "task_title": "Rubric reflection",
                    "grading_mode": "Criteria",
                    "rubric_scoring_strategy": "Separate Criteria",
                    "due_date": "2026-04-03 10:00:00",
                    "delivery_mode": "Assess",
                    "allow_feedback": 1,
                    "max_points": None,
                    "task_type": "Assignment",
                },
                {
                    "delivery_id": "TDL-0002",
                    "task_title": "Quiz score",
                    "grading_mode": "Points",
                    "rubric_scoring_strategy": None,
                    "due_date": "2026-04-04 10:00:00",
                    "delivery_mode": "Assess",
                    "allow_feedback": 0,
                    "max_points": 20.0,
                    "task_type": "Quiz",
                },
            ],
        )
        self.assertEqual(
            payload["students"],
            [
                {
                    "student": "STU-1",
                    "student_name": "Ada Lovelace",
                    "student_id": "S-001",
                    "student_image": None,
                }
            ],
        )
        self.assertEqual(
            payload["cells"][0]["official"]["criteria"], [{"criteria": "CRIT-1", "level": "Secure", "points": 4}]
        )
        self.assertTrue(payload["cells"][0]["flags"]["has_new_submission"])
        self.assertTrue(payload["cells"][1]["flags"]["is_published"])

    def test_get_grid_hides_grade_value_when_official_grade_is_missing(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Delivery":
                    return [
                        {
                            "name": "TDL-0001",
                            "task": "TASK-1",
                            "grading_mode": "Points",
                            "rubric_scoring_strategy": None,
                            "due_date": "2026-04-03 10:00:00",
                            "delivery_mode": "Assess",
                            "allow_feedback": 1,
                            "max_points": 20,
                        }
                    ]
                if doctype == "Task":
                    return [{"name": "TASK-1", "title": "Quiz score", "task_type": "Quiz"}]
                if doctype == "Task Outcome":
                    return [
                        {
                            "name": "OUT-1",
                            "task_delivery": "TDL-0001",
                            "student": "STU-1",
                            "grading_status": "Finalized",
                            "procedural_status": None,
                            "has_submission": 1,
                            "has_new_submission": 0,
                            "official_score": 20,
                            "official_grade": None,
                            "official_grade_value": 0,
                            "official_feedback": "",
                            "is_complete": 0,
                            "is_published": 0,
                        }
                    ]
                return []

            frappe.get_all = fake_get_all

            module = _import_fresh_gradebook()
            module.gradebook_support._can_read_gradebook = lambda: True
            module.gradebook_support._resolve_gradebook_scope = lambda school, academic_year, course: {}
            module.gradebook_support._assert_group_access = lambda student_group: None
            module.gradebook_support._get_student_display_map = lambda student_ids: {"STU-1": "Ada Lovelace"}
            module.gradebook_support._get_student_meta_map = lambda student_ids: {
                "STU-1": {"student_id": "S-001", "student_image": None}
            }

            payload = module.get_grid(
                {
                    "school": "SCH-1",
                    "academic_year": "2025-2026",
                    "limit": 1,
                }
            )

        self.assertEqual(payload["cells"][0]["official"]["score"], 20)
        self.assertIsNone(payload["cells"][0]["official"]["grade"])
        self.assertIsNone(payload["cells"][0]["official"]["grade_value"])

    def test_update_task_student_rejects_feedback_when_comments_disabled(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    return {"name": "OUT-1", "task_delivery": "TDL-1", "official_score": None}
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 0,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            with self.assertRaises(StubValidationError):
                module.update_task_student("OUT-1", {"feedback": "Needs a stronger explanation."})

    def test_update_task_student_allows_criteria_comment_before_any_rubric_score(self):
        submitted_payloads = []

        task_contribution_service = types.ModuleType("ifitwala_ed.assessment.task_contribution_service")
        task_contribution_service.submit_contribution = lambda payload, contributor=None: (
            submitted_payloads.append((payload, contributor)) or {"contribution": "TCO-1"}
        )

        with stubbed_frappe(
            extra_modules=_gradebook_stub_modules(task_contribution_service=task_contribution_service)
        ) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    if fieldname == ["name", "task_delivery", "official_score", "grading_status", "is_published"]:
                        return {
                            "name": "OUT-1",
                            "task_delivery": "TDL-1",
                            "official_score": None,
                            "grading_status": "Not Started",
                            "is_published": 0,
                        }
                    return {
                        "name": "OUT-1",
                        "official_score": None,
                        "official_feedback": "Focus on examples.",
                        "grading_status": "Not Started",
                        "is_complete": 0,
                        "is_published": 0,
                        "modified": "2026-04-02 18:30:00",
                    }
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Criteria",
                        "allow_feedback": 1,
                    }
                return None

            frappe.db.get_value = fake_get_value
            frappe.db.get_values = lambda *args, **kwargs: []

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None
            module.gradebook_support._resolve_or_create_stub_submission_id = lambda task_student, payload: "SUB-1"

            payload = module.update_task_student("OUT-1", {"feedback": "Focus on examples."})

        self.assertEqual(
            submitted_payloads,
            [
                (
                    {
                        "task_outcome": "OUT-1",
                        "feedback": "Focus on examples.",
                        "task_submission": "SUB-1",
                    },
                    "unit.test@example.com",
                )
            ],
        )
        self.assertEqual(payload["feedback"], "Focus on examples.")

    def test_update_task_student_routes_assessed_completion_to_contribution_judgment(self):
        submitted_payloads = []

        task_contribution_service = types.ModuleType("ifitwala_ed.assessment.task_contribution_service")
        task_contribution_service.submit_contribution = lambda payload, contributor=None: (
            submitted_payloads.append((payload, contributor)) or {"contribution": "TCO-1"}
        )

        with stubbed_frappe(
            extra_modules=_gradebook_stub_modules(task_contribution_service=task_contribution_service)
        ) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    if fieldname == ["name", "task_delivery", "official_score", "grading_status", "is_published"]:
                        return {
                            "name": "OUT-1",
                            "task_delivery": "TDL-1",
                            "official_score": None,
                            "grading_status": "Not Started",
                            "is_published": 0,
                        }
                    return {
                        "name": "OUT-1",
                        "official_score": None,
                        "official_feedback": "Marked complete.",
                        "grading_status": "Finalized",
                        "is_complete": 1,
                        "is_published": 0,
                        "modified": "2026-04-17 18:05:00",
                    }
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Completion",
                        "allow_feedback": 1,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None
            module.gradebook_support._resolve_or_create_stub_submission_id = lambda task_student, payload: "SUB-1"

            payload = module.update_task_student("OUT-1", {"complete": 1, "feedback": "Marked complete."})

        self.assertEqual(
            submitted_payloads,
            [
                (
                    {
                        "task_outcome": "OUT-1",
                        "feedback": "Marked complete.",
                        "judgment_code": "complete",
                        "task_submission": "SUB-1",
                    },
                    "unit.test@example.com",
                )
            ],
        )
        self.assertEqual(payload["complete"], 1)
        self.assertEqual(payload["feedback"], "Marked complete.")

    def test_update_task_student_keeps_assign_only_completion_on_direct_outcome_path(self):
        submitted_payloads = []
        completion_calls = []

        task_contribution_service = types.ModuleType("ifitwala_ed.assessment.task_contribution_service")
        task_contribution_service.submit_contribution = lambda payload, contributor=None: submitted_payloads.append(
            (payload, contributor)
        )
        task_outcome_service = types.ModuleType("ifitwala_ed.assessment.task_outcome_service")
        task_outcome_service.set_assign_only_completion = (
            lambda outcome_id, *, is_complete, expected_student=None, ignore_permissions=False: (
                completion_calls.append(
                    {
                        "outcome_id": outcome_id,
                        "is_complete": is_complete,
                        "expected_student": expected_student,
                        "ignore_permissions": ignore_permissions,
                    }
                )
                or {"outcome": outcome_id, "is_complete": is_complete, "completed_on": "2026-04-17 18:10:00"}
            )
        )

        with stubbed_frappe(
            extra_modules=_gradebook_stub_modules(
                task_contribution_service=task_contribution_service,
                task_outcome_service=task_outcome_service,
            )
        ) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    if fieldname == ["name", "task_delivery", "official_score", "grading_status", "is_published"]:
                        return {
                            "name": "OUT-1",
                            "task_delivery": "TDL-1",
                            "official_score": None,
                            "grading_status": "Not Started",
                            "is_published": 0,
                        }
                    return {
                        "name": "OUT-1",
                        "official_score": None,
                        "official_feedback": None,
                        "grading_status": "Not Started",
                        "is_complete": 1,
                        "is_published": 0,
                        "modified": "2026-04-17 18:10:00",
                    }
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "delivery_mode": "Assign Only",
                        "grading_mode": "Completion",
                        "allow_feedback": 0,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            payload = module.update_task_student("OUT-1", {"complete": 1})

        self.assertEqual(submitted_payloads, [])
        self.assertEqual(
            completion_calls,
            [
                {
                    "outcome_id": "OUT-1",
                    "is_complete": 1,
                    "expected_student": None,
                    "ignore_permissions": False,
                }
            ],
        )
        self.assertEqual(payload["complete"], 1)

    def test_update_task_student_rejects_released_status_from_generic_status_save(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    if fieldname == ["name", "task_delivery", "official_score", "grading_status", "is_published"]:
                        return {
                            "name": "OUT-1",
                            "task_delivery": "TDL-1",
                            "official_score": None,
                            "grading_status": "Finalized",
                            "is_published": 0,
                        }
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 0,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            with self.assertRaises(StubValidationError):
                module.update_task_student("OUT-1", {"status": "Released"})

    def test_update_task_student_rejects_status_change_while_outcome_is_released(self):
        with stubbed_frappe(extra_modules=_gradebook_stub_modules()) as frappe:

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Task Outcome":
                    if fieldname == ["name", "task_delivery", "official_score", "grading_status", "is_published"]:
                        return {
                            "name": "OUT-1",
                            "task_delivery": "TDL-1",
                            "official_score": None,
                            "grading_status": "Released",
                            "is_published": 1,
                        }
                if doctype == "Task Delivery":
                    return {
                        "name": "TDL-1",
                        "student_group": "GRP-1",
                        "delivery_mode": "Assess",
                        "grading_mode": "Points",
                        "allow_feedback": 0,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = _import_fresh_gradebook()
            module.gradebook_support._can_write_gradebook = lambda: True
            module.gradebook_support._assert_group_access = lambda student_group: None

            with self.assertRaises(StubValidationError):
                module.update_task_student("OUT-1", {"status": "Needs Review"})
