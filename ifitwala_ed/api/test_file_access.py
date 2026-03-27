# ifitwala_ed/api/test_file_access.py

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.file_access import (
    build_academic_file_open_url,
    build_admissions_file_open_url,
    build_guardian_file_open_url,
    download_guardian_file,
    resolve_academic_file_open_url,
    resolve_guardian_file_open_url,
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

    def test_build_guardian_file_open_url_includes_context(self):
        url = build_guardian_file_open_url(
            file_name="FILE-GRD-1",
            context_doctype="Guardian",
            context_name="GRD-0001",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_guardian_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-GRD-1")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Guardian")
        self.assertEqual((query.get("context_name") or [None])[0], "GRD-0001")

    def test_resolve_guardian_file_open_url_keeps_external_links(self):
        external = "https://cdn.example.com/avatar.webp"
        self.assertEqual(
            resolve_guardian_file_open_url(
                file_name="FILE-GRD-EXT",
                file_url=external,
                context_doctype="Guardian",
                context_name="GRD-0001",
            ),
            external,
        )

    def test_download_guardian_file_streams_private_file_for_linked_guardian(self):
        file_row = {
            "name": "FILE-GRD-1",
            "file_url": "/private/files/Guardian/GRD-0001/thumb_guardian.webp",
            "file_name": "thumb_guardian.webp",
            "is_private": 1,
            "attached_to_doctype": "Guardian",
            "attached_to_name": "GRD-0001",
        }

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="guardian@example.com"),
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._resolve_guardian_from_file", return_value="GRD-0001"),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", return_value="GRD-0001"),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=b"guardian-bytes"),
        ):
            frappe.local.response = {}
            download_guardian_file(
                file="FILE-GRD-1",
                context_doctype="Guardian",
                context_name="GRD-0001",
            )

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), "thumb_guardian.webp")
        self.assertEqual(frappe.local.response.get("filecontent"), b"guardian-bytes")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")

    def test_download_guardian_file_denies_other_guardian(self):
        file_row = {
            "name": "FILE-GRD-1",
            "file_url": "/private/files/Guardian/GRD-0001/thumb_guardian.webp",
            "file_name": "thumb_guardian.webp",
            "is_private": 1,
            "attached_to_doctype": "Guardian",
            "attached_to_name": "GRD-0001",
        }

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="other@example.com"),
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._resolve_guardian_from_file", return_value="GRD-0001"),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", return_value="GRD-9999"),
        ):
            with self.assertRaises(frappe.PermissionError):
                download_guardian_file(
                    file="FILE-GRD-1",
                    context_doctype="Guardian",
                    context_name="GRD-0001",
                )
