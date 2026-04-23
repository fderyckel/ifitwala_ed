from __future__ import annotations

import types
from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubPermissionError, import_fresh, stubbed_frappe


def _artifact_service_modules(
    feedback_service=None,
    content_uploads=None,
    file_access=None,
    pdf_module=None,
    drive_authority=None,
    drive_tasks=None,
):
    feedback = feedback_service or types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
    if not hasattr(feedback, "build_released_feedback_detail_payload"):
        feedback.build_released_feedback_detail_payload = lambda outcome_id, audience="student", submission_id=None: {
            "outcome_id": outcome_id,
            "task_submission": submission_id or "TSU-1",
            "audience": audience,
            "context": {
                "title": "Source Analysis",
                "course_name": "English",
                "student": "STU-1",
            },
            "grade_visible": False,
            "feedback_visible": True,
            "official": {"score": None, "grade": None, "grade_value": None, "feedback": None},
            "feedback": {
                "submission_version": 2,
                "summary": {
                    "overall": "Strong evidence selection.",
                    "strengths": "Clear thesis.",
                    "improvements": "Tighten your final paragraph.",
                    "next_steps": "Revise the conclusion.",
                },
                "priorities": [{"id": "PRI-1", "title": "Clarify the conclusion", "detail": "Keep it tighter."}],
                "items": [
                    {
                        "id": "TFI-1",
                        "page": 2,
                        "intent": "issue",
                        "comment": "This paragraph needs a clearer link back to the claim.",
                    }
                ],
                "rubric_snapshot": [
                    {
                        "assessment_criteria": "CRIT-1",
                        "criteria_name": "Analysis",
                        "level": "Secure",
                        "points": 4,
                        "feedback": "Good support overall.",
                    }
                ],
            },
        }
    if not hasattr(feedback, "build_released_result_payload"):
        feedback.build_released_result_payload = lambda outcome_id, audience="student", submission_id=None: {
            "outcome_id": outcome_id,
            "task_submission": submission_id or "TSU-1",
            "audience": audience,
            "grade_visible": False,
            "feedback_visible": True,
            "publication": {
                "feedback_visibility": "student",
                "grade_visibility": "hidden",
                "derived_from_legacy_outcome": False,
                "legacy_outcome_published": False,
                "legacy_published_on": None,
                "legacy_published_by": None,
            },
            "official": {"score": None, "grade": None, "grade_value": None, "feedback": None},
            "feedback": {
                "submission_version": 2,
                "summary": {
                    "overall": "Strong evidence selection.",
                    "strengths": "Clear thesis.",
                    "improvements": "Tighten your final paragraph.",
                    "next_steps": "Revise the conclusion.",
                },
                "items": [],
                "modified": "2026-04-23 08:30:00",
                "modified_by": "teacher@example.com",
            },
        }

    uploads = content_uploads or types.ModuleType("ifitwala_ed.integrations.drive.content_uploads")
    if not hasattr(uploads, "upload_content_via_drive"):
        uploads.upload_content_via_drive = lambda **kwargs: (
            {},
            {"preview_status": "pending"},
            SimpleNamespace(
                name="FILE-1",
                file_name=kwargs.get("file_name"),
                file_url="/private/files/released-feedback.pdf",
            ),
        )

    file_access_module = file_access or types.ModuleType("ifitwala_ed.api.file_access")
    if not hasattr(file_access_module, "resolve_academic_file_open_url"):
        file_access_module.resolve_academic_file_open_url = (
            lambda *, file_name, file_url, context_doctype=None, context_name=None, **kwargs: (
                f"/open?file={file_name}&context_doctype={context_doctype}&context_name={context_name}"
            )
        )
    if not hasattr(file_access_module, "resolve_academic_file_preview_url"):
        file_access_module.resolve_academic_file_preview_url = (
            lambda *, file_name, file_url, context_doctype=None, context_name=None, **kwargs: (
                f"/preview?file={file_name}&context_doctype={context_doctype}&context_name={context_name}"
            )
        )

    pdf = pdf_module or types.ModuleType("frappe.utils.pdf")
    if not hasattr(pdf, "get_pdf"):
        pdf.get_pdf = lambda html: b"%PDF-artifact"

    authority = drive_authority or types.ModuleType("ifitwala_ed.integrations.drive.authority")
    if not hasattr(authority, "get_current_drive_file_for_slot"):
        authority.get_current_drive_file_for_slot = lambda **kwargs: None

    tasks = drive_tasks or types.ModuleType("ifitwala_ed.integrations.drive.tasks")
    if not hasattr(tasks, "build_task_feedback_export_upload_contract"):
        tasks.build_task_feedback_export_upload_contract = lambda doc, audience="student": {
            "slot": f"feedback_export__released__{audience}",
        }

    return {
        "ifitwala_ed.assessment.task_feedback_service": feedback,
        "ifitwala_ed.integrations.drive.content_uploads": uploads,
        "ifitwala_ed.integrations.drive.authority": authority,
        "ifitwala_ed.integrations.drive.tasks": tasks,
        "ifitwala_ed.api.file_access": file_access_module,
        "frappe.utils.pdf": pdf,
    }


class TestTaskFeedbackArtifactService(TestCase):
    def test_export_released_feedback_pdf_uploads_governed_feedback_artifact(self):
        captured: dict[str, object] = {}

        feedback = types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
        feedback.build_released_feedback_detail_payload = lambda outcome_id, audience="student", submission_id=None: {
            "outcome_id": outcome_id,
            "task_submission": submission_id or "TSU-1",
            "audience": audience,
            "context": {
                "title": "Source Analysis",
                "course_name": "English",
                "student": "STU-1",
            },
            "grade_visible": False,
            "feedback_visible": True,
            "official": {"score": None, "grade": None, "grade_value": None, "feedback": None},
            "feedback": {
                "submission_version": 2,
                "summary": {"overall": "Strong evidence selection."},
                "priorities": [],
                "items": [],
                "rubric_snapshot": [],
            },
        }

        uploads = types.ModuleType("ifitwala_ed.integrations.drive.content_uploads")

        def fake_upload_content_via_drive(**kwargs):
            captured.update(kwargs)
            return (
                {},
                {"preview_status": "pending"},
                SimpleNamespace(
                    name="FILE-1",
                    file_name=kwargs.get("file_name"),
                    file_url="/private/files/released-feedback.pdf",
                ),
            )

        uploads.upload_content_via_drive = fake_upload_content_via_drive

        with stubbed_frappe(
            extra_modules=_artifact_service_modules(
                feedback_service=feedback,
                content_uploads=uploads,
            )
        ) as frappe:
            frappe.db.get_value = lambda doctype, name_or_filters, fieldname=None, as_dict=False: (
                "Student One" if doctype == "Student" and fieldname == "student_name" else None
            )

            module = import_fresh("ifitwala_ed.assessment.task_feedback_artifact_service")
            payload = module.export_released_feedback_pdf("OUT-1")

        self.assertEqual(captured["workflow_id"], "task.feedback_export")
        self.assertEqual(captured["workflow_payload"]["task_submission"], "TSU-1")
        self.assertEqual(captured["workflow_payload"]["artifact_kind"], "released_feedback_pdf")
        self.assertEqual(payload["task_submission"], "TSU-1")
        self.assertEqual(payload["preview_status"], "pending")
        self.assertIn("/open?file=FILE-1", payload["open_url"])
        self.assertEqual(payload["attachment_preview"]["kind"], "pdf")

    def test_export_released_feedback_pdf_requires_released_feedback(self):
        feedback = types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
        feedback.build_released_feedback_detail_payload = lambda outcome_id, audience="student", submission_id=None: {
            "outcome_id": outcome_id,
            "task_submission": submission_id or "TSU-1",
            "audience": audience,
            "context": {"title": "Source Analysis", "student": "STU-1"},
            "grade_visible": False,
            "feedback_visible": False,
            "official": {"score": None, "grade": None, "grade_value": None, "feedback": None},
            "feedback": None,
        }

        with stubbed_frappe(extra_modules=_artifact_service_modules(feedback_service=feedback)):
            module = import_fresh("ifitwala_ed.assessment.task_feedback_artifact_service")
            with self.assertRaises(StubPermissionError):
                module.export_released_feedback_pdf("OUT-1")

    def test_export_released_feedback_pdf_reuses_current_artifact_when_fresh(self):
        uploads = types.ModuleType("ifitwala_ed.integrations.drive.content_uploads")
        uploads.upload_content_via_drive = lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("upload should not be called when current artifact is fresh")
        )

        authority = types.ModuleType("ifitwala_ed.integrations.drive.authority")
        authority.get_current_drive_file_for_slot = lambda **kwargs: {
            "file": "FILE-1",
            "preview_status": "ready",
            "modified": "2026-04-23 10:00:00",
            "creation": "2026-04-23 09:58:00",
        }

        with stubbed_frappe(
            extra_modules=_artifact_service_modules(
                content_uploads=uploads,
                drive_authority=authority,
            )
        ) as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Student" and fieldname == "student_name":
                    return "Student One"
                if doctype == "Task Submission" and name_or_filters == "TSU-1":
                    return {"name": "TSU-1", "student": "STU-1", "school": "SCH-1"}
                if doctype == "Task Outcome" and name_or_filters == "OUT-1" and fieldname == "modified":
                    return "2026-04-23 09:00:00"
                if doctype == "File" and name_or_filters == "FILE-1":
                    return {
                        "name": "FILE-1",
                        "file_name": "released-feedback.pdf",
                        "file_url": "/private/files/released-feedback.pdf",
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.assessment.task_feedback_artifact_service")
            payload = module.export_released_feedback_pdf("OUT-1")

        self.assertEqual(payload["file_id"], "FILE-1")
        self.assertEqual(payload["preview_status"], "ready")

    def test_get_current_released_feedback_pdf_artifact_returns_none_when_stale(self):
        authority = types.ModuleType("ifitwala_ed.integrations.drive.authority")
        authority.get_current_drive_file_for_slot = lambda **kwargs: {
            "file": "FILE-1",
            "preview_status": "ready",
            "modified": "2026-04-23 08:00:00",
            "creation": "2026-04-23 08:00:00",
        }

        with stubbed_frappe(
            extra_modules=_artifact_service_modules(
                drive_authority=authority,
            )
        ) as frappe:

            def fake_get_value(doctype, name_or_filters, fieldname=None, as_dict=False):
                if doctype == "Task Submission" and name_or_filters == "TSU-1":
                    return {"name": "TSU-1", "student": "STU-1", "school": "SCH-1"}
                if doctype == "Task Outcome" and name_or_filters == "OUT-1" and fieldname == "modified":
                    return "2026-04-23 09:00:00"
                if doctype == "File" and name_or_filters == "FILE-1":
                    return {
                        "name": "FILE-1",
                        "file_name": "released-feedback.pdf",
                        "file_url": "/private/files/released-feedback.pdf",
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.assessment.task_feedback_artifact_service")
            payload = module.get_current_released_feedback_pdf_artifact("OUT-1")

        self.assertIsNone(payload)
