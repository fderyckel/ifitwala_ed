from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _released_feedback_stub_modules(
    task_feedback_service=None,
    task_feedback_thread_service=None,
    task_feedback_artifact_service=None,
    task_submission_service=None,
    courses_service=None,
    guardian_home_service=None,
):
    feedback_service = task_feedback_service or types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
    if not hasattr(feedback_service, "build_released_feedback_detail_payload"):
        feedback_service.build_released_feedback_detail_payload = lambda outcome_id, audience="student": {
            "outcome_id": outcome_id,
            "task_submission": "TSU-1",
            "audience": audience,
            "context": {"title": "Source Analysis"},
            "grade_visible": audience == "student",
            "feedback_visible": True,
            "publication": {
                "feedback_visibility": "student",
                "grade_visibility": "hidden",
                "derived_from_legacy_outcome": False,
                "legacy_outcome_published": False,
            },
            "official": {"score": None, "grade": None, "grade_value": None, "feedback": None},
            "feedback": {
                "task_submission": "TSU-1",
                "submission_version": 2,
                "summary": {
                    "overall": "Strong evidence selection.",
                    "strengths": "",
                    "improvements": "",
                    "next_steps": "",
                },
                "priorities": [],
                "items": [],
                "rubric_snapshot": [],
                "threads": [],
            },
            "allowed_actions": {
                "can_reply": audience == "student",
                "can_set_learner_state": audience == "student",
                "can_view_threads": True,
            },
        }

    thread_service = task_feedback_thread_service or types.ModuleType(
        "ifitwala_ed.assessment.task_feedback_thread_service"
    )
    if not hasattr(thread_service, "save_student_reply"):
        thread_service.save_student_reply = lambda payload, actor=None: {
            "thread_id": "TFT-1",
            "target_type": "feedback_item",
            "target_feedback_item": payload.get("target_feedback_item"),
            "target_priority": None,
            "summary_field": None,
            "learner_state": "none",
            "thread_status": "open",
            "messages": [
                {
                    "id": "MSG-1",
                    "author": actor,
                    "author_role": "student",
                    "message_kind": payload.get("message_kind"),
                    "body": payload.get("body"),
                    "created": "2026-04-22 14:00:00",
                }
            ],
            "modified": "2026-04-22 14:00:00",
            "modified_by": actor,
        }
    if not hasattr(thread_service, "save_student_learner_state"):
        thread_service.save_student_learner_state = lambda payload, actor=None: {
            "thread_id": "TFT-1",
            "target_type": "feedback_item",
            "target_feedback_item": payload.get("target_feedback_item"),
            "target_priority": None,
            "summary_field": None,
            "learner_state": payload.get("learner_state"),
            "thread_status": "open",
            "messages": [],
            "modified": "2026-04-22 14:05:00",
            "modified_by": actor,
        }

    task_submission = task_submission_service or types.ModuleType("ifitwala_ed.api.task_submission")
    if not hasattr(task_submission, "serialize_task_submission_evidence"):
        task_submission.serialize_task_submission_evidence = lambda row, is_latest_version=None: {
            "submission_id": row.get("name"),
            "version": row.get("version"),
            "submitted_on": row.get("submitted_on"),
            "submitted_by": row.get("submitted_by"),
            "origin": row.get("submission_origin"),
            "is_stub": row.get("is_stub"),
            "evidence_note": row.get("evidence_note"),
            "is_cloned": row.get("is_cloned"),
            "cloned_from": row.get("cloned_from"),
            "text_content": row.get("text_content"),
            "link_url": row.get("link_url"),
            "attachments": [
                {
                    "row_name": "ATT-PDF",
                    "kind": "file",
                    "file_name": "submission.pdf",
                    "mime_type": "application/pdf",
                    "extension": "pdf",
                    "attachment": {
                        "id": "ATT-PDF",
                        "surface": "task_submission.evidence",
                        "display_name": "Submitted PDF",
                        "kind": "pdf",
                        "preview_mode": "pdf_embed",
                        "preview_url": "/preview/submission",
                        "open_url": "/open/submission",
                        "mime_type": "application/pdf",
                        "extension": "pdf",
                    },
                }
            ],
            "annotation_readiness": {
                "mode": "reduced",
                "reason_code": "ocr_pending",
                "title": "Reduced annotation mode",
                "message": "PDF text extraction is still pending.",
                "attachment_row_name": "ATT-PDF",
                "attachment_file_name": "submission.pdf",
                "preview_status": "ready",
                "preview_url": "/preview/submission",
                "open_url": "/open/submission",
            },
        }

    courses = courses_service or types.ModuleType("ifitwala_ed.api.courses")
    if not hasattr(courses, "_require_student_name_for_session_user"):
        courses._require_student_name_for_session_user = lambda: "STU-1"

    guardian_home = guardian_home_service or types.ModuleType("ifitwala_ed.api.guardian_home")
    if not hasattr(guardian_home, "_resolve_guardian_scope"):
        guardian_home._resolve_guardian_scope = lambda user: (
            {"guardian": "GRD-1"},
            [{"student": "STU-1"}],
        )

    artifact_service = task_feedback_artifact_service or types.ModuleType(
        "ifitwala_ed.assessment.task_feedback_artifact_service"
    )
    if not hasattr(artifact_service, "export_released_feedback_pdf"):
        artifact_service.export_released_feedback_pdf = lambda outcome_id, audience="student": {
            "file_id": "FILE-1",
            "file_name": "released-feedback.pdf",
            "task_submission": "TSU-1",
            "submission_version": 2,
            "preview_status": "pending",
            "open_url": "/open/feedback-pdf",
            "preview_url": "/preview/feedback-pdf",
            "attachment_preview": {
                "display_name": "Released feedback PDF",
                "kind": "pdf",
                "preview_mode": "pdf_embed",
                "preview_url": "/preview/feedback-pdf",
                "open_url": "/open/feedback-pdf",
                "mime_type": "application/pdf",
                "extension": "pdf",
            },
        }
    if not hasattr(artifact_service, "get_current_released_feedback_pdf_artifact"):
        artifact_service.get_current_released_feedback_pdf_artifact = (
            lambda outcome_id, audience="student", detail=None, submission_id=None: {
                "file_id": "FILE-1",
                "file_name": "released-feedback.pdf",
                "task_submission": "TSU-1",
                "submission_version": 2,
                "preview_status": "ready",
                "open_url": "/open/feedback-pdf",
                "preview_url": "/preview/feedback-pdf",
                "attachment_preview": {
                    "display_name": "Released feedback PDF",
                    "kind": "pdf",
                    "preview_mode": "pdf_embed",
                    "preview_url": "/preview/feedback-pdf",
                    "open_url": "/open/feedback-pdf",
                    "mime_type": "application/pdf",
                    "extension": "pdf",
                },
            }
        )

    return {
        "ifitwala_ed.assessment.task_feedback_artifact_service": artifact_service,
        "ifitwala_ed.assessment.task_feedback_service": feedback_service,
        "ifitwala_ed.assessment.task_feedback_thread_service": thread_service,
        "ifitwala_ed.api.task_submission": task_submission,
        "ifitwala_ed.api.courses": courses,
        "ifitwala_ed.api.guardian_home": guardian_home,
    }


class TestReleasedFeedbackApi(TestCase):
    def test_student_detail_uses_submission_evidence_as_document_context(self):
        with stubbed_frappe(extra_modules=_released_feedback_stub_modules()) as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Outcome" and name_or_filters == "OUT-1":
                    if fieldname == "student":
                        return "STU-1"
                if doctype == "Task Submission" and name_or_filters == "TSU-1":
                    return {
                        "name": "TSU-1",
                        "version": 2,
                        "submitted_on": "2026-04-22 13:45:00",
                        "submitted_by": "student@example.com",
                        "submission_origin": "Student Upload",
                        "is_stub": 0,
                        "evidence_note": "",
                        "is_cloned": 0,
                        "cloned_from": "",
                        "text_content": "Submitted response",
                        "link_url": "",
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.api.released_feedback")
            payload = module.get_student_released_feedback_detail("OUT-1")

        self.assertEqual(payload["audience"], "student")
        self.assertEqual(payload["document"]["submission"]["submission_id"], "TSU-1")
        self.assertEqual(payload["document"]["primary_attachment"]["row_name"], "ATT-PDF")
        self.assertEqual(payload["document"]["primary_attachment"]["attachment"]["open_url"], "/open/submission")
        self.assertEqual(payload["released_feedback_artifact"]["open_url"], "/open/feedback-pdf")

    def test_guardian_detail_stays_text_first_without_document_surface(self):
        with stubbed_frappe(extra_modules=_released_feedback_stub_modules()) as frappe:
            frappe.db.get_value = lambda doctype, name_or_filters, fieldname=None, as_dict=False: (
                "STU-1" if doctype == "Task Outcome" and fieldname == "student" else None
            )

            module = import_fresh("ifitwala_ed.api.released_feedback")
            payload = module.get_guardian_released_feedback_detail("OUT-1")

        self.assertEqual(payload["audience"], "guardian")
        self.assertIsNone(payload["document"])
        self.assertIsNone(payload["released_feedback_artifact"])

    def test_student_reply_uses_named_thread_mutation(self):
        captured: dict[str, object] = {}
        thread_service = types.ModuleType("ifitwala_ed.assessment.task_feedback_thread_service")

        def fake_save_student_reply(payload, actor=None):
            captured["payload"] = payload
            captured["actor"] = actor
            return {
                "thread_id": "TFT-1",
                "target_type": "feedback_item",
                "target_feedback_item": payload.get("target_feedback_item"),
                "target_priority": None,
                "summary_field": None,
                "learner_state": "none",
                "thread_status": "open",
                "messages": [],
                "modified": "2026-04-22 14:00:00",
                "modified_by": actor,
            }

        thread_service.save_student_reply = fake_save_student_reply
        thread_service.save_student_learner_state = lambda payload, actor=None: {}

        with stubbed_frappe(
            extra_modules=_released_feedback_stub_modules(task_feedback_thread_service=thread_service)
        ) as frappe:
            frappe.db.get_value = lambda doctype, name_or_filters, fieldname=None, as_dict=False: (
                "STU-1" if doctype == "Task Outcome" and fieldname == "student" else None
            )

            module = import_fresh("ifitwala_ed.api.released_feedback")
            payload = module.save_student_feedback_reply(
                {
                    "outcome_id": "OUT-1",
                    "submission_id": "TSU-1",
                    "target_type": "feedback_item",
                    "target_feedback_item": "TFI-1",
                    "message_kind": "clarification",
                    "body": "Could you clarify this next step?",
                }
            )

        self.assertEqual(payload["thread"]["thread_id"], "TFT-1")
        self.assertEqual(captured["payload"]["target_feedback_item"], "TFI-1")
        self.assertEqual(captured["payload"]["message_kind"], "clarification")
        self.assertEqual(captured["actor"], "unit.test@example.com")

    def test_student_export_uses_artifact_service(self):
        captured: dict[str, object] = {}
        artifact_service = types.ModuleType("ifitwala_ed.assessment.task_feedback_artifact_service")

        def fake_export(outcome_id, audience="student"):
            captured["outcome_id"] = outcome_id
            captured["audience"] = audience
            return {
                "file_id": "FILE-1",
                "file_name": "released-feedback.pdf",
                "task_submission": "TSU-1",
                "submission_version": 2,
                "preview_status": "pending",
                "open_url": "/open/feedback-pdf",
                "preview_url": "/preview/feedback-pdf",
                "attachment_preview": {"kind": "pdf", "preview_mode": "pdf_embed"},
            }

        artifact_service.export_released_feedback_pdf = fake_export

        with stubbed_frappe(
            extra_modules=_released_feedback_stub_modules(task_feedback_artifact_service=artifact_service)
        ) as frappe:
            frappe.db.get_value = lambda doctype, name_or_filters, fieldname=None, as_dict=False: (
                "STU-1" if doctype == "Task Outcome" and fieldname == "student" else None
            )

            module = import_fresh("ifitwala_ed.api.released_feedback")
            payload = module.export_student_released_feedback_pdf("OUT-1")

        self.assertEqual(captured["outcome_id"], "OUT-1")
        self.assertEqual(captured["audience"], "student")
        self.assertEqual(payload["artifact"]["open_url"], "/open/feedback-pdf")
