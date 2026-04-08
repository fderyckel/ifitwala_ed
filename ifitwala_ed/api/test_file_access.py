# ifitwala_ed/api/test_file_access.py

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.file_access import (
    build_academic_file_open_url,
    build_admissions_file_open_url,
    build_employee_file_open_url,
    build_guardian_file_open_url,
    build_org_communication_attachment_open_url,
    download_academic_file,
    download_employee_file,
    download_guardian_file,
    open_org_communication_attachment,
    resolve_academic_file_open_url,
    resolve_employee_file_open_url,
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

    def test_open_org_communication_attachment_redirects_to_drive_preview_grant(self):
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
                return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}
            if doctype == "Drive Binding":
                return {"drive_file": "DRIVE-0001", "file": "FILE-0001"}
            if doctype == "Drive File" and filters == "DRIVE-0001" and fieldname == "preview_status":
                return "ready"
            return None

        with (
            patch("ifitwala_ed.api.file_access._require_authenticated_user", return_value="staff@example.com"),
            patch("ifitwala_ed.api.file_access.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.file_access.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.api.file_access.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.file_access.frappe.get_doc", return_value=comm_doc),
            patch(
                "ifitwala_ed.api.file_access._load_drive_access_callable",
                return_value=lambda **_kwargs: {"url": "https://preview.example.com/policy.pdf"},
            ),
        ):
            frappe.local.response = {}
            open_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://preview.example.com/policy.pdf",
        )
