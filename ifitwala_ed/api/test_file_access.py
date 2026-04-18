# ifitwala_ed/api/test_file_access.py

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.file_access import (
    build_academic_file_open_url,
    build_academic_file_preview_url,
    build_academic_file_thumbnail_url,
    build_admissions_file_open_url,
    build_employee_file_open_url,
    build_guardian_file_open_url,
    build_org_communication_attachment_open_url,
    build_org_communication_attachment_preview_url,
    build_org_communication_attachment_thumbnail_url,
    build_public_website_media_url,
    download_academic_file,
    download_employee_file,
    download_guardian_file,
    open_org_communication_attachment,
    open_public_website_media,
    preview_academic_file,
    preview_org_communication_attachment,
    resolve_academic_file_open_url,
    resolve_academic_file_preview_url,
    resolve_academic_file_thumbnail_url,
    resolve_employee_file_open_url,
    resolve_guardian_file_open_url,
    resolve_public_website_media_url,
    thumbnail_academic_file,
    thumbnail_org_communication_attachment,
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

    def test_build_academic_file_preview_url_supports_share_scope(self):
        url = build_academic_file_preview_url(
            file_name="FILE-ACADEMIC-1",
            share_token="token-abc",
            viewer_email="viewer@example.com",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.preview_academic_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-ACADEMIC-1")
        self.assertEqual((query.get("share_token") or [None])[0], "token-abc")
        self.assertEqual((query.get("viewer_email") or [None])[0], "viewer@example.com")

    def test_build_academic_file_thumbnail_url_supports_share_scope(self):
        url = build_academic_file_thumbnail_url(
            file_name="FILE-ACADEMIC-1",
            share_token="token-abc",
            viewer_email="viewer@example.com",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file")
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

    def test_resolve_academic_file_preview_url_prefers_stable_route_when_file_name_exists(self):
        self.assertEqual(
            resolve_academic_file_preview_url(
                file_name="FILE-EXT",
                file_url="https://cdn.example.com/demo.pdf",
                context_doctype="Student",
                context_name="STU-0001",
            ),
            "/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-EXT&context_doctype=Student&context_name=STU-0001",
        )

    def test_resolve_academic_file_thumbnail_url_prefers_stable_route_when_file_name_exists(self):
        self.assertEqual(
            resolve_academic_file_thumbnail_url(
                file_name="FILE-EXT",
                file_url="https://cdn.example.com/demo.pdf",
                context_doctype="Student",
                context_name="STU-0001",
            ),
            "/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-EXT&context_doctype=Student&context_name=STU-0001",
        )

    def test_resolve_academic_file_open_url_recovers_file_name_from_file_url_for_private_files(self):
        with patch("ifitwala_ed.api.file_access.frappe.db.get_value", return_value="FILE-ACADEMIC-1") as get_value:
            url = resolve_academic_file_open_url(
                file_name=None,
                file_url="/private/files/submission.pdf",
                context_doctype="Task Submission",
                context_name="TSU-0001",
            )

        parsed = urlparse(url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_academic_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-ACADEMIC-1")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Task Submission")
        self.assertEqual((query.get("context_name") or [None])[0], "TSU-0001")
        get_value.assert_called_once_with("File", {"file_url": "/private/files/submission.pdf"}, "name")

    def test_resolve_academic_file_preview_url_recovers_file_name_from_file_url_for_private_files(self):
        with patch("ifitwala_ed.api.file_access.frappe.db.get_value", return_value="FILE-ACADEMIC-1") as get_value:
            url = resolve_academic_file_preview_url(
                file_name=None,
                file_url="/private/files/submission.pdf",
                context_doctype="Task Submission",
                context_name="TSU-0001",
            )

        parsed = urlparse(url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.preview_academic_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-ACADEMIC-1")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Task Submission")
        self.assertEqual((query.get("context_name") or [None])[0], "TSU-0001")
        get_value.assert_called_once_with("File", {"file_url": "/private/files/submission.pdf"}, "name")

    def test_resolve_academic_file_thumbnail_url_recovers_file_name_from_file_url_for_private_files(self):
        with patch("ifitwala_ed.api.file_access.frappe.db.get_value", return_value="FILE-ACADEMIC-1") as get_value:
            url = resolve_academic_file_thumbnail_url(
                file_name=None,
                file_url="/private/files/submission.pdf",
                context_doctype="Task Submission",
                context_name="TSU-0001",
            )

        parsed = urlparse(url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-ACADEMIC-1")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Task Submission")
        self.assertEqual((query.get("context_name") or [None])[0], "TSU-0001")
        get_value.assert_called_once_with("File", {"file_url": "/private/files/submission.pdf"}, "name")

    def test_resolve_academic_file_open_url_never_leaks_unresolved_private_file_urls(self):
        with patch("ifitwala_ed.api.file_access.frappe.db.get_value", return_value=None):
            self.assertIsNone(
                resolve_academic_file_open_url(
                    file_name=None,
                    file_url="/private/files/submission.pdf",
                    context_doctype="Task Submission",
                    context_name="TSU-0001",
                )
            )

    def test_resolve_academic_file_preview_url_never_leaks_unresolved_private_file_urls(self):
        with patch("ifitwala_ed.api.file_access.frappe.db.get_value", return_value=None):
            self.assertIsNone(
                resolve_academic_file_preview_url(
                    file_name=None,
                    file_url="/private/files/submission.pdf",
                    context_doctype="Task Submission",
                    context_name="TSU-0001",
                )
            )

    def test_resolve_academic_file_thumbnail_url_never_leaks_unresolved_private_file_urls(self):
        with patch("ifitwala_ed.api.file_access.frappe.db.get_value", return_value=None):
            self.assertIsNone(
                resolve_academic_file_thumbnail_url(
                    file_name=None,
                    file_url="/private/files/submission.pdf",
                    context_doctype="Task Submission",
                    context_name="TSU-0001",
                )
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

    def test_build_employee_file_open_url_includes_context(self):
        url = build_employee_file_open_url(
            file_name="FILE-EMP-1",
            context_doctype="Employee",
            context_name="EMP-0001",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_employee_file")
        self.assertEqual((query.get("file") or [None])[0], "FILE-EMP-1")
        self.assertEqual((query.get("context_doctype") or [None])[0], "Employee")
        self.assertEqual((query.get("context_name") or [None])[0], "EMP-0001")

    def test_build_org_communication_attachment_open_url_includes_row_context(self):
        url = build_org_communication_attachment_open_url(
            org_communication="COMM-0001",
            row_name="row-001",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(
            parsed.path,
            "/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment",
        )
        self.assertEqual((query.get("org_communication") or [None])[0], "COMM-0001")
        self.assertEqual((query.get("row_name") or [None])[0], "row-001")

    def test_build_org_communication_attachment_preview_url_includes_row_context(self):
        url = build_org_communication_attachment_preview_url(
            org_communication="COMM-0001",
            row_name="row-001",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(
            parsed.path,
            "/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment",
        )
        self.assertEqual((query.get("org_communication") or [None])[0], "COMM-0001")
        self.assertEqual((query.get("row_name") or [None])[0], "row-001")

    def test_build_org_communication_attachment_thumbnail_url_includes_row_context(self):
        url = build_org_communication_attachment_thumbnail_url(
            org_communication="COMM-0001",
            row_name="row-001",
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(
            parsed.path,
            "/api/method/ifitwala_ed.api.file_access.thumbnail_org_communication_attachment",
        )
        self.assertEqual((query.get("org_communication") or [None])[0], "COMM-0001")
        self.assertEqual((query.get("row_name") or [None])[0], "row-001")

    def test_build_public_website_media_url_includes_file(self):
        url = build_public_website_media_url(file_name="FILE-PUBLIC-1")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.open_public_website_media")
        self.assertEqual((query.get("file") or [None])[0], "FILE-PUBLIC-1")

    def test_resolve_public_website_media_keeps_public_files(self):
        self.assertEqual(
            resolve_public_website_media_url(
                file_name="FILE-PUBLIC-1",
                file_url="/files/logo.png",
            ),
            "/files/logo.png",
        )

    def test_resolve_public_website_media_wraps_private_files(self):
        self.assertEqual(
            resolve_public_website_media_url(
                file_name="FILE-PUBLIC-1",
                file_url="/private/files/logo.png",
            ),
            "/api/method/ifitwala_ed.api.file_access.open_public_website_media?file=FILE-PUBLIC-1",
        )

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

    def test_resolve_employee_file_open_url_keeps_external_links(self):
        external = "https://cdn.example.com/avatar.webp"
        self.assertEqual(
            resolve_employee_file_open_url(
                file_name="FILE-EMP-EXT",
                file_url=external,
                context_doctype="Employee",
                context_name="EMP-0001",
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

    def test_download_employee_file_streams_private_file_for_scoped_staff(self):
        file_row = {
            "name": "FILE-EMP-1",
            "file_url": "/private/files/Employee/EMP-0001/thumb_employee.webp",
            "file_name": "thumb_employee.webp",
            "is_private": 1,
            "attached_to_doctype": "Employee",
            "attached_to_name": "EMP-0001",
        }

        def fake_get_value(doctype, filters, fieldname, as_dict=False):
            if doctype == "File Classification":
                return frappe._dict(
                    {
                        "primary_subject_type": "Employee",
                        "primary_subject_id": "EMP-0001",
                    }
                )
            return None

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.frappe.db.exists", return_value=True),
            patch("ifitwala_ed.api.file_access.has_active_employee_profile", return_value=True),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=b"employee-bytes"),
        ):
            frappe.local.response = {}
            download_employee_file(
                file="FILE-EMP-1",
                context_doctype="Employee",
                context_name="EMP-0001",
            )

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), "thumb_employee.webp")
        self.assertEqual(frappe.local.response.get("filecontent"), b"employee-bytes")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")

    def test_download_employee_file_denies_non_employee_user(self):
        file_row = {
            "name": "FILE-EMP-1",
            "file_url": "/private/files/Employee/EMP-0001/thumb_employee.webp",
            "file_name": "thumb_employee.webp",
            "is_private": 1,
            "attached_to_doctype": "Employee",
            "attached_to_name": "EMP-0001",
        }

        def fake_get_value(doctype, filters, fieldname, as_dict=False):
            if doctype == "File Classification":
                return frappe._dict(
                    {
                        "primary_subject_type": "Employee",
                        "primary_subject_id": "EMP-0001",
                    }
                )
            return None

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.frappe.db.exists", return_value=True),
            patch("ifitwala_ed.api.file_access.has_active_employee_profile", return_value=False),
        ):
            with self.assertRaises(frappe.PermissionError):
                download_employee_file(
                    file="FILE-EMP-1",
                    context_doctype="Employee",
                    context_name="EMP-0001",
                )

    def test_download_academic_file_streams_supporting_material_for_scoped_student(self):
        file_row = {
            "name": "FILE-MAT-1",
            "file_url": "/private/files/Courses/COURSE-1/material.pdf",
            "file_name": "material.pdf",
            "is_private": 1,
            "attached_to_doctype": "Supporting Material",
            "attached_to_name": "MAT-1",
        }

        with (
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="student@example.com"),
            patch(
                "ifitwala_ed.api.file_access._resolve_supporting_material_context_for_file",
                return_value=("MAT-1", "COURSE-1"),
            ),
            patch("ifitwala_ed.api.file_access._assert_internal_material_context", return_value=None),
            patch("ifitwala_ed.curriculum.materials.user_can_read_supporting_material", return_value=True),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=b"material-bytes"),
        ):
            frappe.local.response = {}
            download_academic_file(
                file="FILE-MAT-1",
                context_doctype="Supporting Material",
                context_name="MAT-1",
            )

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), "material.pdf")
        self.assertEqual(frappe.local.response.get("filecontent"), b"material-bytes")

    def test_download_academic_file_denies_supporting_material_outside_scope(self):
        file_row = {
            "name": "FILE-MAT-1",
            "file_url": "/private/files/Courses/COURSE-1/material.pdf",
            "file_name": "material.pdf",
            "is_private": 1,
            "attached_to_doctype": "Supporting Material",
            "attached_to_name": "MAT-1",
        }

        with (
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="student@example.com"),
            patch(
                "ifitwala_ed.api.file_access._resolve_supporting_material_context_for_file",
                return_value=("MAT-1", "COURSE-1"),
            ),
            patch("ifitwala_ed.api.file_access._assert_internal_material_context", return_value=None),
            patch("ifitwala_ed.curriculum.materials.user_can_read_supporting_material", return_value=False),
        ):
            with self.assertRaises(frappe.PermissionError):
                download_academic_file(
                    file="FILE-MAT-1",
                    context_doctype="Supporting Material",
                    context_name="MAT-1",
                )

    def test_preview_academic_file_redirects_to_drive_preview_grant_when_ready(self):
        file_row = {
            "name": "FILE-MAT-1",
            "file_url": "/private/files/Courses/COURSE-1/material.pdf",
            "file_name": "material.pdf",
            "is_private": 1,
            "attached_to_doctype": "Supporting Material",
            "attached_to_name": "MAT-1",
        }
        grant_calls = []

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Drive File" and filters == {"file": "FILE-MAT-1"}:
                return {"name": "DRIVE-0001", "preview_status": "ready"}
            return None

        def fake_load(attribute):
            grant_calls.append(attribute)
            return lambda **_kwargs: {"url": "https://preview.example.com/material.pdf"}

        with (
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="student@example.com"),
            patch(
                "ifitwala_ed.api.file_access._resolve_supporting_material_context_for_file",
                return_value=("MAT-1", "COURSE-1"),
            ),
            patch("ifitwala_ed.api.file_access._assert_internal_material_context", return_value=None),
            patch("ifitwala_ed.curriculum.materials.user_can_read_supporting_material", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access._load_drive_access_callable", side_effect=fake_load),
        ):
            frappe.local.response = {}
            preview_academic_file(
                file="FILE-MAT-1",
                context_doctype="Supporting Material",
                context_name="MAT-1",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(frappe.local.response.get("location"), "https://preview.example.com/material.pdf")
        self.assertEqual(grant_calls, ["issue_preview_grant"])

    def test_preview_academic_file_falls_back_to_download_grant_when_preview_not_ready(self):
        file_row = {
            "name": "FILE-MAT-1",
            "file_url": "/private/files/Courses/COURSE-1/material.pdf",
            "file_name": "material.pdf",
            "is_private": 1,
            "attached_to_doctype": "Supporting Material",
            "attached_to_name": "MAT-1",
        }
        grant_calls = []

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Drive File" and filters == {"file": "FILE-MAT-1"}:
                return {"name": "DRIVE-0001", "preview_status": "pending"}
            return None

        def fake_load(attribute):
            grant_calls.append(attribute)
            return lambda **_kwargs: {"url": "https://download.example.com/material.pdf"}

        with (
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="student@example.com"),
            patch(
                "ifitwala_ed.api.file_access._resolve_supporting_material_context_for_file",
                return_value=("MAT-1", "COURSE-1"),
            ),
            patch("ifitwala_ed.api.file_access._assert_internal_material_context", return_value=None),
            patch("ifitwala_ed.curriculum.materials.user_can_read_supporting_material", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access._load_drive_access_callable", side_effect=fake_load),
        ):
            frappe.local.response = {}
            preview_academic_file(
                file="FILE-MAT-1",
                context_doctype="Supporting Material",
                context_name="MAT-1",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(frappe.local.response.get("location"), "https://download.example.com/material.pdf")
        self.assertEqual(grant_calls, ["issue_download_grant"])

    def test_open_org_communication_attachment_redirects_to_drive_download_grant(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.pdf",
            external_url=None,
        )

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        comm_doc = _CommDoc()

        grant_calls = []

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            if doctype == "Drive File" and filters == "DRIVE-0001" and fieldname == "preview_status":
                return "ready"
            return None

        def fake_load(attribute):
            grant_calls.append(attribute)
            return lambda **_kwargs: {"url": "https://download.example.com/policy.pdf"}

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch("ifitwala_ed.api.file_access._load_drive_access_callable", side_effect=fake_load),
        ):
            frappe.local.response = {}
            open_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://download.example.com/policy.pdf",
        )
        self.assertEqual(grant_calls, ["issue_download_grant"])

    def test_preview_org_communication_attachment_redirects_to_drive_preview_grant_when_ready(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.pdf",
            external_url=None,
        )

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        comm_doc = _CommDoc()
        grant_calls = []

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            if doctype == "Drive File" and filters == "DRIVE-0001" and fieldname == "preview_status":
                return "ready"
            return None

        def fake_load(attribute):
            grant_calls.append(attribute)
            return lambda **_kwargs: {"url": "https://preview.example.com/policy.pdf"}

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch("ifitwala_ed.api.file_access._load_drive_access_callable", side_effect=fake_load),
        ):
            frappe.local.response = {}
            preview_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://preview.example.com/policy.pdf",
        )
        self.assertEqual(grant_calls, ["issue_preview_grant"])

    def test_thumbnail_org_communication_attachment_uses_thumb_grant_and_reuses_cache(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.png",
            external_url=None,
        )

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        class _FakeCache:
            def __init__(self):
                self.values = {}

            def get_value(self, key):
                return self.values.get(key)

            def set_value(self, key, value, expires_in_sec=None):
                self.values[key] = value

        comm_doc = _CommDoc()
        cache = _FakeCache()
        grant_requests = []

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            if doctype == "Drive File" and filters == "DRIVE-0001" and fieldname == ["name", "current_version"]:
                return {"name": "DRIVE-0001", "current_version": "DFV-0001"}
            return None

        def fake_load(attribute):
            self.assertEqual(attribute, "issue_preview_grant")

            def _grant(**kwargs):
                grant_requests.append(kwargs)
                return {"url": "https://thumb.example.com/policy-thumb.webp"}

            return _grant

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch("ifitwala_ed.api.file_access.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.file_access._load_drive_access_callable", side_effect=fake_load),
        ):
            frappe.local.response = {}
            thumbnail_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

            first_headers = frappe.local.response.get("headers") or {}
            self.assertEqual(first_headers.get("Cache-Control"), "private, max-age=240, must-revalidate")
            self.assertEqual(frappe.local.response.get("location"), "https://thumb.example.com/policy-thumb.webp")

            frappe.local.response = {}
            thumbnail_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(
            grant_requests,
            [{"drive_file_id": "DRIVE-0001", "derivative_role": "thumb"}],
        )

    def test_thumbnail_org_communication_attachment_cache_rotates_when_current_version_changes(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.png",
            external_url=None,
        )

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        class _FakeCache:
            def __init__(self):
                self.values = {}

            def get_value(self, key):
                return self.values.get(key)

            def set_value(self, key, value, expires_in_sec=None):
                self.values[key] = value

        comm_doc = _CommDoc()
        cache = _FakeCache()
        current_version = {"value": "DFV-0001"}
        grant_requests = []

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            if doctype == "Drive File" and filters == "DRIVE-0001" and fieldname == ["name", "current_version"]:
                return {"name": "DRIVE-0001", "current_version": current_version["value"]}
            return None

        def fake_load(attribute):
            self.assertEqual(attribute, "issue_preview_grant")

            def _grant(**kwargs):
                grant_requests.append(kwargs)
                return {"url": f"https://thumb.example.com/{current_version['value']}.webp"}

            return _grant

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch("ifitwala_ed.api.file_access.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.file_access._load_drive_access_callable", side_effect=fake_load),
        ):
            frappe.local.response = {}
            thumbnail_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

            current_version["value"] = "DFV-0002"
            frappe.local.response = {}
            thumbnail_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(
            grant_requests,
            [
                {"drive_file_id": "DRIVE-0001", "derivative_role": "thumb"},
                {"drive_file_id": "DRIVE-0001", "derivative_role": "thumb"},
            ],
        )

    def test_preview_org_communication_attachment_expands_academic_admin_org_scope_without_default_school(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.pdf",
            external_url=None,
        )

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        comm_doc = _CommDoc()

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": None, "organization": "ORG-ROOT"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            if doctype == "Drive File" and filters == "DRIVE-0001" and fieldname == "preview_status":
                return "ready"
            return None

        with (
            patch(
                "ifitwala_ed.api.file_access._require_authenticated_user",
                return_value="academic-admin@example.com",
            ),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch(
                "ifitwala_ed.api.org_comm_utils.get_descendant_organizations",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.api.org_comm_utils.frappe.get_all",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch(
                "ifitwala_ed.api.file_access.check_audience_match",
                return_value=True,
            ) as audience_match_mock,
            patch(
                "ifitwala_ed.api.file_access._load_drive_access_callable",
                return_value=lambda **_kwargs: {"url": "https://preview.example.com/policy.pdf"},
            ),
        ):
            frappe.local.response = {}
            preview_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        audience_match_mock.assert_called_once_with(
            "COMM-0001",
            "academic-admin@example.com",
            ["Academic Admin"],
            {
                "name": "EMP-1",
                "school": None,
                "organization": "ORG-ROOT",
                "organization_names": ["ORG-ROOT", "ORG-CHILD"],
                "school_names": ["SCH-ROOT", "SCH-CHILD"],
            },
            allow_owner=True,
        )
        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://preview.example.com/policy.pdf",
        )

    def test_preview_org_communication_attachment_falls_back_to_download_when_preview_not_ready(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.pdf",
            external_url=None,
        )

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        comm_doc = _CommDoc()
        grant_calls = []

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            if doctype == "Drive File" and filters == "DRIVE-0001" and fieldname == "preview_status":
                return "pending"
            return None

        def fake_load(attribute):
            grant_calls.append(attribute)
            return lambda **_kwargs: {"url": "https://download.example.com/policy.pdf"}

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch("ifitwala_ed.api.file_access._load_drive_access_callable", side_effect=fake_load),
        ):
            frappe.local.response = {}
            preview_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://download.example.com/policy.pdf",
        )
        self.assertEqual(grant_calls, ["issue_download_grant"])

    def test_open_org_communication_attachment_streams_inline_when_target_is_raw_private_path(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.pdf",
            external_url=None,
        )
        file_row = {
            "name": "FILE-0001",
            "file_url": "/private/files/policy.pdf",
            "file_name": "policy.pdf",
            "is_private": 1,
        }

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        comm_doc = _CommDoc()

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            return None

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch(
                "ifitwala_ed.api.file_access._resolve_drive_file_grant_target_url",
                return_value="/private/files/policy.pdf",
            ),
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=b"policy-bytes"),
        ):
            frappe.local.response = {}
            open_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), "policy.pdf")
        self.assertEqual(frappe.local.response.get("filecontent"), b"policy-bytes")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")
        self.assertEqual(frappe.local.response.get("content_type"), "application/pdf")
        self.assertIsNone(frappe.local.response.get("location"))

    def test_preview_org_communication_attachment_streams_inline_when_target_is_raw_private_path(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.png",
            external_url=None,
        )
        file_row = {
            "name": "FILE-0001",
            "file_url": "/private/files/policy.png",
            "file_name": "policy.png",
            "is_private": 1,
        }

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        comm_doc = _CommDoc()

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            return None

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch(
                "ifitwala_ed.api.file_access._resolve_drive_file_grant_target_url",
                return_value="/private/files/policy.png",
            ),
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=b"image-bytes"),
        ):
            frappe.local.response = {}
            preview_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), "policy.png")
        self.assertEqual(frappe.local.response.get("filecontent"), b"image-bytes")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")
        self.assertEqual(frappe.local.response.get("content_type"), "image/png")
        self.assertIsNone(frappe.local.response.get("location"))

    def test_thumbnail_org_communication_attachment_streams_inline_when_target_is_raw_private_path(self):
        attachment_row = frappe._dict(
            name="row-001",
            file="/private/files/policy.png",
            external_url=None,
        )
        file_row = {
            "name": "FILE-0001",
            "file_url": "/private/files/policy.png",
            "file_name": "policy.png",
            "is_private": 1,
        }

        class _CommDoc:
            name = "COMM-0001"

            def get(self, fieldname):
                if fieldname == "attachments":
                    return [attachment_row]
                return []

        comm_doc = _CommDoc()

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            return None

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch(
                "ifitwala_ed.api.file_access._resolve_cached_thumbnail_target_url",
                return_value="/private/files/policy.png",
            ),
            patch("ifitwala_ed.api.file_access._resolve_any_file_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=b"thumb-bytes"),
        ):
            frappe.local.response = {}
            thumbnail_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), "policy.png")
        self.assertEqual(frappe.local.response.get("filecontent"), b"thumb-bytes")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")
        self.assertEqual(frappe.local.response.get("content_type"), "image/png")
        self.assertEqual(
            (frappe.local.response.get("headers") or {}).get("Cache-Control"),
            "private, max-age=240, must-revalidate",
        )
        self.assertIsNone(frappe.local.response.get("location"))

    def test_thumbnail_academic_file_uses_thumb_grant_and_private_cache_headers(self):
        file_row = {
            "name": "FILE-MAT-1",
            "file_url": "/private/files/Courses/COURSE-1/material.png",
            "file_name": "material.png",
            "is_private": 1,
            "attached_to_doctype": "Supporting Material",
            "attached_to_name": "MAT-1",
        }

        class _FakeCache:
            def __init__(self):
                self.values = {}

            def get_value(self, key):
                return self.values.get(key)

            def set_value(self, key, value, expires_in_sec=None):
                self.values[key] = value

        grant_requests = []

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Drive File" and filters == {"file": "FILE-MAT-1"}:
                return {"name": "DRIVE-0001", "preview_status": "ready", "current_version": "DFV-0001"}
            if doctype == "Drive File" and filters == "DRIVE-0001" and fieldname == ["name", "current_version"]:
                return {"name": "DRIVE-0001", "current_version": "DFV-0001"}
            return None

        def fake_load(attribute):
            self.assertEqual(attribute, "issue_preview_grant")

            def _grant(**kwargs):
                grant_requests.append(kwargs)
                return {"url": "https://thumb.example.com/material-thumb.webp"}

            return _grant

        with (
            patch("ifitwala_ed.api.file_access._resolve_authorized_academic_file", return_value=file_row),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.frappe.cache", return_value=_FakeCache()),
            patch("ifitwala_ed.api.file_access._load_drive_access_callable", side_effect=fake_load),
        ):
            frappe.local.response = {}
            thumbnail_academic_file(
                file="FILE-MAT-1",
                context_doctype="Supporting Material",
                context_name="MAT-1",
            )

        self.assertEqual(
            grant_requests,
            [{"drive_file_id": "DRIVE-0001", "derivative_role": "thumb"}],
        )
        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://thumb.example.com/material-thumb.webp",
        )
        self.assertEqual(
            (frappe.local.response.get("headers") or {}).get("Cache-Control"),
            "private, max-age=240, must-revalidate",
        )

    def test_thumbnail_academic_file_streams_inline_when_safe_thumb_target_is_unavailable(self):
        file_row = {
            "name": "FILE-MAT-1",
            "file_url": "/private/files/Courses/COURSE-1/material.png",
            "file_name": "material.png",
            "is_private": 1,
            "attached_to_doctype": "Supporting Material",
            "attached_to_name": "MAT-1",
        }

        def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
            if doctype == "Drive File" and filters == {"file": "FILE-MAT-1"}:
                return {"name": "DRIVE-0001", "preview_status": "ready", "current_version": "DFV-0001"}
            return None

        with (
            patch("ifitwala_ed.api.file_access._resolve_authorized_academic_file", return_value=file_row),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access._resolve_cached_thumbnail_target_url", return_value=None),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=b"material-bytes"),
        ):
            frappe.local.response = {}
            thumbnail_academic_file(
                file="FILE-MAT-1",
                context_doctype="Supporting Material",
                context_name="MAT-1",
            )

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), "material.png")
        self.assertEqual(frappe.local.response.get("filecontent"), b"material-bytes")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")
        self.assertEqual(frappe.local.response.get("content_type"), "image/png")
        self.assertEqual(
            (frappe.local.response.get("headers") or {}).get("Cache-Control"),
            "private, max-age=240, must-revalidate",
        )
        self.assertIsNone(frappe.local.response.get("location"))

    def test_open_public_website_media_streams_private_logo_for_guest(self):
        file_row = {
            "name": "FILE-PUBLIC-1",
            "file_url": "/private/files/Organization/root/logo.png",
            "file_name": "logo.png",
            "is_private": 1,
            "organization": "ORG-ROOT",
            "school": "",
        }

        with (
            patch("ifitwala_ed.api.file_access._resolve_public_website_media_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._assert_public_website_media_visible"),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=b"logo-bytes"),
        ):
            frappe.local.response = {}
            open_public_website_media(file="FILE-PUBLIC-1")

        self.assertEqual(frappe.local.response.get("type"), "download")
        self.assertEqual(frappe.local.response.get("filename"), "logo.png")
        self.assertEqual(frappe.local.response.get("filecontent"), b"logo-bytes")
        self.assertEqual(frappe.local.response.get("display_content_as"), "inline")

    def test_open_public_website_media_redirects_to_drive_preview_when_file_bytes_missing(self):
        file_row = {
            "name": "FILE-PUBLIC-1",
            "file_url": "/private/files/Organization/root/logo.png",
            "file_name": "logo.png",
            "is_private": 1,
            "organization": "ORG-ROOT",
            "school": "",
        }

        with (
            patch("ifitwala_ed.api.file_access._resolve_public_website_media_row", return_value=file_row),
            patch("ifitwala_ed.api.file_access._assert_public_website_media_visible"),
            patch("ifitwala_ed.api.file_access._read_file_bytes", return_value=None),
            patch(
                "ifitwala_ed.api.file_access._resolve_public_website_media_grant_url",
                return_value="https://preview.example.com/logo.png",
            ),
        ):
            frappe.local.response = {}
            open_public_website_media(file="FILE-PUBLIC-1")

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(frappe.local.response.get("location"), "https://preview.example.com/logo.png")
