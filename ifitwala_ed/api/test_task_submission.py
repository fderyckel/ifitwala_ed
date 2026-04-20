# ifitwala_ed/api/test_task_submission.py

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.task_submission import get_latest_submission


class TestTaskSubmissionApi(FrappeTestCase):
    @patch("ifitwala_ed.api.task_submission._require_authenticated")
    @patch("ifitwala_ed.api.task_submission._require_student_outcome_access")
    @patch("ifitwala_ed.api.task_submission.frappe.get_all")
    def test_get_latest_submission_serializes_governed_preview_and_open_urls(
        self,
        mock_get_all,
        mock_require_outcome_access,
        mock_require_authenticated,
    ):
        mock_require_authenticated.return_value = None
        mock_require_outcome_access.return_value = "STU-0001"
        mock_get_all.side_effect = [
            [
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
                    "text_content": "Updated submission",
                    "link_url": "",
                }
            ],
            [
                {
                    "name": "ATT-0001",
                    "file": "/private/files/task-submission-proof.pdf",
                    "external_url": "",
                    "description": "Proof",
                    "public": 0,
                    "file_name": "task-submission-proof.pdf",
                    "file_size": 256,
                }
            ],
            [
                {
                    "name": "FILE-TASK-0001",
                    "file_url": "/private/files/task-submission-proof.pdf",
                    "creation": "2026-03-05 09:00:00",
                }
            ],
            [
                {
                    "file": "FILE-TASK-0001",
                    "preview_status": "ready",
                    "current_version": "DFV-TASK-0001",
                }
            ],
            [
                {
                    "name": "DFV-TASK-0001",
                    "mime_type": "application/pdf",
                }
            ],
        ]

        payload = get_latest_submission(outcome_id="TOUT-0001")
        attachments = payload.get("attachments") or []
        self.assertEqual(len(attachments), 1)
        self.assertEqual(payload.get("origin"), "Student Upload")
        self.assertFalse(payload.get("is_stub"))
        self.assertEqual(payload.get("evidence_note"), "Updated evidence")

        secure_url = (attachments[0].get("file") or "").strip()
        self.assertTrue(secure_url)
        self.assertNotIn("/private/files/", secure_url)

        parsed = urlparse(secure_url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_academic_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-TASK-0001")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Task Submission")
        self.assertEqual((query.get("context_name") or [None])[0], "TSU-2026-00001")
        preview_url = (attachments[0].get("preview_url") or "").strip()
        preview_parsed = urlparse(preview_url)
        preview_query = parse_qs(preview_parsed.query)
        self.assertEqual(preview_parsed.path, "/api/method/ifitwala_ed.api.file_access.preview_academic_file")
        self.assertEqual((preview_query.get("file") or [None])[0], "FILE-TASK-0001")
        self.assertEqual(attachments[0].get("preview_status"), "ready")
        self.assertEqual(attachments[0].get("mime_type"), "application/pdf")
        self.assertEqual(attachments[0].get("extension"), "pdf")
        self.assertEqual((attachments[0].get("open_url") or "").strip(), secure_url)
        self.assertEqual(attachments[0].get("attachment_preview", {}).get("owner_doctype"), "Task Submission")
        self.assertEqual(attachments[0].get("attachment_preview", {}).get("kind"), "pdf")
        self.assertTrue(attachments[0].get("attachment_preview", {}).get("is_latest_version"))
        self.assertEqual(payload.get("annotation_readiness", {}).get("mode"), "reduced")
        self.assertEqual(payload.get("annotation_readiness", {}).get("reason_code"), "pdf_preview_ready")
