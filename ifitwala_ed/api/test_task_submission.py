# ifitwala_ed/api/test_task_submission.py

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.task_submission import get_latest_submission


class TestTaskSubmissionApi(FrappeTestCase):
    @patch("ifitwala_ed.api.task_submission._require_authenticated")
    @patch("ifitwala_ed.api.task_submission.frappe.get_all")
    def test_get_latest_submission_rewrites_private_file_links_to_secure_endpoint(
        self,
        mock_get_all,
        mock_require_authenticated,
    ):
        mock_require_authenticated.return_value = None
        mock_get_all.side_effect = [
            [
                {
                    "name": "TSU-2026-00001",
                    "version": 2,
                    "submitted_on": "2026-03-05 09:00:00",
                    "text_content": "Updated submission",
                    "link_url": "",
                }
            ],
            [
                {
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
        ]

        payload = get_latest_submission(outcome_id="TOUT-0001")
        attachments = payload.get("attachments") or []
        self.assertEqual(len(attachments), 1)

        secure_url = (attachments[0].get("file") or "").strip()
        self.assertTrue(secure_url)
        self.assertNotIn("/private/files/", secure_url)

        parsed = urlparse(secure_url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_academic_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-TASK-0001")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Task Submission")
        self.assertEqual((query.get("context_name") or [None])[0], "TSU-2026-00001")
