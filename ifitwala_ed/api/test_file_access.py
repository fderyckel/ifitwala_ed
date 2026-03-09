# ifitwala_ed/api/test_file_access.py

from urllib.parse import parse_qs, urlparse

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.file_access import (
    build_academic_file_open_url,
    build_admissions_file_open_url,
    resolve_academic_file_open_url,
)


class TestFileAccessUrlContracts(FrappeTestCase):
    def test_build_admissions_file_open_url_includes_context(self):
        url = build_admissions_file_open_url(
            file_name="FILE-001",
            context_doctype="Student Applicant",
            context_name="APPL-0001",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_admissions_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-001")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Student Applicant")
        self.assertEqual((query.get("context_name") or [None])[0], "APPL-0001")

    def test_build_academic_file_open_url_supports_share_scope(self):
        url = build_academic_file_open_url(
            file_name="FILE-ACADEMIC-1",
            share_token="token-abc",
            viewer_email="viewer@example.com",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_academic_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-ACADEMIC-1")
        self.assertEqual((query.get("share_token") or [None])[0], "token-abc")
        self.assertEqual((query.get("viewer_email") or [None])[0], "viewer@example.com")

    def test_resolve_academic_file_open_url_keeps_external_links(self):
        external = "https://cdn.example.com/demo.pdf"
        self.assertEqual(
            resolve_academic_file_open_url(
                file_name="FILE-EXT",
                file_url=external,
                context_doctype="Student",
                context_name="STU-0001",
            ),
            external,
        )
