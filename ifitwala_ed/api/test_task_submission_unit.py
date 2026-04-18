from __future__ import annotations

import types
from unittest import TestCase
from urllib.parse import parse_qs, urlparse

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _task_submission_stub_modules():
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

    return {
        "ifitwala_ed.api.file_access": file_access,
        "ifitwala_ed.assessment.task_submission_service": types.ModuleType(
            "ifitwala_ed.assessment.task_submission_service"
        ),
    }


class TestTaskSubmissionApiUnit(TestCase):
    def test_get_latest_submission_includes_annotation_readiness_for_governed_pdf(self):
        with stubbed_frappe(extra_modules=_task_submission_stub_modules()) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Submission":
                    return [
                        {
                            "name": "TSU-2026-00001",
                            "version": 2,
                            "submitted_on": "2026-03-05 09:00:00",
                            "submitted_by": "student@example.com",
                            "submission_origin": "Student Upload",
                            "is_stub": 0,
                            "evidence_note": "Updated evidence",
                            "is_cloned": 0,
                            "cloned_from": "",
                            "text_content": "",
                            "link_url": "",
                        }
                    ]
                if doctype == "Attached Document":
                    return [
                        {
                            "name": "ATT-0001",
                            "file": "/private/files/task-submission-proof.pdf",
                            "external_url": "",
                            "description": "Proof",
                            "public": 0,
                            "file_name": "task-submission-proof.pdf",
                            "file_size": 256,
                        }
                    ]
                if doctype == "File":
                    return [
                        {
                            "name": "FILE-TASK-0001",
                            "file_url": "/private/files/task-submission-proof.pdf",
                            "creation": "2026-03-05 09:00:00",
                        }
                    ]
                if doctype == "Drive File":
                    return [
                        {
                            "file": "FILE-TASK-0001",
                            "preview_status": "ready",
                            "current_version": "DFV-TASK-0001",
                        }
                    ]
                if doctype == "Drive File Version":
                    return [{"name": "DFV-TASK-0001", "mime_type": "application/pdf"}]
                return []

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.task_submission")
            module._require_authenticated = lambda: None

            payload = module.get_latest_submission(outcome_id="TOUT-0001")

        attachments = payload.get("attachments") or []
        self.assertEqual(len(attachments), 1)
        self.assertEqual(payload.get("origin"), "Student Upload")
        self.assertFalse(payload.get("is_stub"))
        self.assertEqual(payload.get("evidence_note"), "Updated evidence")
        self.assertEqual(attachments[0].get("mime_type"), "application/pdf")
        self.assertEqual(attachments[0].get("extension"), "pdf")
        self.assertEqual(attachments[0].get("preview_status"), "ready")
        self.assertEqual(payload.get("annotation_readiness", {}).get("mode"), "reduced")
        self.assertEqual(payload.get("annotation_readiness", {}).get("reason_code"), "pdf_preview_ready")

        secure_url = (attachments[0].get("file") or "").strip()
        preview_url = (attachments[0].get("preview_url") or "").strip()
        secure_parsed = urlparse(secure_url)
        preview_parsed = urlparse(preview_url)
        secure_query = parse_qs(secure_parsed.query)
        preview_query = parse_qs(preview_parsed.query)

        self.assertEqual(
            secure_parsed.path,
            "/api/method/ifitwala_ed.api.file_access.download_academic_file",
        )
        self.assertEqual(
            preview_parsed.path,
            "/api/method/ifitwala_ed.api.file_access.preview_academic_file",
        )
        self.assertEqual((secure_query.get("context_name") or [None])[0], "TSU-2026-00001")
        self.assertEqual((preview_query.get("file") or [None])[0], "FILE-TASK-0001")

    def test_get_latest_submission_detects_pdf_from_extension_when_mime_and_filename_are_missing(self):
        with stubbed_frappe(extra_modules=_task_submission_stub_modules()) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0, pluck=None):
                if doctype == "Task Submission":
                    return [
                        {
                            "name": "TSU-2026-00002",
                            "version": 3,
                            "submitted_on": "2026-03-06 11:00:00",
                            "submitted_by": "student@example.com",
                            "submission_origin": "Student Upload",
                            "is_stub": 0,
                            "evidence_note": "",
                            "is_cloned": 0,
                            "cloned_from": "",
                            "text_content": "",
                            "link_url": "",
                        }
                    ]
                if doctype == "Attached Document":
                    return [
                        {
                            "name": "ATT-0002",
                            "file": "/private/files/annotated-draft.pdf",
                            "external_url": "",
                            "description": "",
                            "public": 0,
                            "file_name": "",
                            "file_size": 512,
                        }
                    ]
                if doctype == "File":
                    return [
                        {
                            "name": "FILE-TASK-0002",
                            "file_url": "/private/files/annotated-draft.pdf",
                            "creation": "2026-03-06 11:00:00",
                        }
                    ]
                if doctype == "Drive File":
                    return [
                        {
                            "file": "FILE-TASK-0002",
                            "preview_status": "pending",
                            "current_version": "DFV-TASK-0002",
                        }
                    ]
                if doctype == "Drive File Version":
                    return [{"name": "DFV-TASK-0002", "mime_type": None}]
                return []

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.task_submission")
            module._require_authenticated = lambda: None

            payload = module.get_latest_submission(outcome_id="TOUT-0002")

        attachments = payload.get("attachments") or []
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get("extension"), "pdf")
        self.assertEqual(attachments[0].get("mime_type"), "application/pdf")
        self.assertEqual(payload.get("annotation_readiness", {}).get("mode"), "reduced")
        self.assertEqual(payload.get("annotation_readiness", {}).get("reason_code"), "pdf_preview_pending")
