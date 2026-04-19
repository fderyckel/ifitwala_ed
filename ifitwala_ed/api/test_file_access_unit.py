from __future__ import annotations

import importlib
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from urllib.parse import parse_qs, urlparse

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _file_access_module():
    admission_access = ModuleType("ifitwala_ed.admission.access")
    admission_access.ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
    admission_access.ADMISSIONS_FAMILY_ROLE = "Admissions Family"
    admission_access.user_can_access_student_applicant = lambda **kwargs: False

    admission_utils = ModuleType("ifitwala_ed.admission.admission_utils")
    admission_utils.has_open_applicant_review_access = lambda **kwargs: False
    admission_utils.has_scoped_staff_access_to_student_applicant = lambda **kwargs: False
    admission_utils.is_admissions_file_staff_user = lambda user: False

    org_comm_utils = ModuleType("ifitwala_ed.api.org_comm_utils")
    org_comm_utils.check_audience_match = lambda *args, **kwargs: False

    routing_policy = ModuleType("ifitwala_ed.routing.policy")
    routing_policy.has_active_employee_profile = lambda **kwargs: True

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.admission.access": admission_access,
            "ifitwala_ed.admission.admission_utils": admission_utils,
            "ifitwala_ed.api.org_comm_utils": org_comm_utils,
            "ifitwala_ed.routing.policy": routing_policy,
        }
    ) as frappe:
        frappe.utils = importlib.import_module("frappe.utils")
        frappe.utils.get_site_path = lambda *parts: "/tmp/missing-file"
        frappe.utils.cint = lambda value: int(value or 0)
        frappe.local = SimpleNamespace(response={})
        frappe.DoesNotExistError = type("StubDoesNotExistError", (Exception,), {})
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.exists = lambda *args, **kwargs: False
        yield import_fresh("ifitwala_ed.api.file_access"), frappe


class TestFileAccessUnit(TestCase):
    def test_get_academic_file_thumbnail_ready_map_marks_only_ready_thumb_derivatives(self):
        with _file_access_module() as (file_access, frappe):

            def fake_sql(query, values=None, as_dict=False):
                self.assertIn("tabDrive File", query)
                self.assertTrue(as_dict)
                self.assertEqual(values, {"file_names": ("FILE-READY", "FILE-WAITING")})
                return [
                    {
                        "file": "FILE-READY",
                        "preview_status": "ready",
                        "current_version": "VER-1",
                        "derivative_name": "DERIV-1",
                    },
                    {
                        "file": "FILE-WAITING",
                        "preview_status": "pending",
                        "current_version": "VER-2",
                        "derivative_name": "",
                    },
                ]

            frappe.db.sql = fake_sql

            ready_map = file_access.get_academic_file_thumbnail_ready_map(["FILE-READY", "FILE-WAITING"])

        self.assertEqual(ready_map, {"FILE-READY": True, "FILE-WAITING": False})

    def test_resolve_academic_file_open_url_recovers_file_name_from_private_file_url(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "File")
                self.assertEqual(filters, {"file_url": "/private/files/submission.pdf"})
                self.assertEqual(fieldname, "name")
                return "FILE-ACADEMIC-1"

            frappe.db.get_value = fake_get_value

            url = file_access.resolve_academic_file_open_url(
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

    def test_resolve_academic_file_open_url_keeps_requested_derivative_role(self):
        with _file_access_module() as (file_access, _frappe):
            url = file_access.resolve_academic_file_open_url(
                file_name="FILE-ACADEMIC-1",
                file_url="/private/files/submission.pdf",
                context_doctype="Student",
                context_name="STU-0001",
                derivative_role="card",
            )

        parsed = urlparse(url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_academic_file")
        self.assertEqual((query.get("derivative_role") or [None])[0], "card")

    def test_resolve_academic_file_preview_url_recovers_file_name_from_private_file_url(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "File")
                self.assertEqual(filters, {"file_url": "/private/files/submission.pdf"})
                self.assertEqual(fieldname, "name")
                return "FILE-ACADEMIC-1"

            frappe.db.get_value = fake_get_value

            url = file_access.resolve_academic_file_preview_url(
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

    def test_resolve_academic_file_thumbnail_url_hides_internal_file_without_ready_thumb(self):
        with _file_access_module() as (file_access, _frappe):
            url = file_access.resolve_academic_file_thumbnail_url(
                file_name="FILE-ACADEMIC-1",
                file_url="/private/files/submission.png",
                context_doctype="Task Submission",
                context_name="TSU-0001",
                thumbnail_ready=False,
            )

        self.assertIsNone(url)

    def test_resolve_academic_file_open_url_hides_unresolved_private_file_url(self):
        with _file_access_module() as (file_access, frappe):
            frappe.db.get_value = lambda *args, **kwargs: None

            url = file_access.resolve_academic_file_open_url(
                file_name=None,
                file_url="/private/files/submission.pdf",
                context_doctype="Task Submission",
                context_name="TSU-0001",
            )

        self.assertIsNone(url)

    def test_resolve_academic_file_preview_url_hides_unresolved_private_file_url(self):
        with _file_access_module() as (file_access, frappe):
            frappe.db.get_value = lambda *args, **kwargs: None

            url = file_access.resolve_academic_file_preview_url(
                file_name=None,
                file_url="/private/files/submission.pdf",
                context_doctype="Task Submission",
                context_name="TSU-0001",
            )

        self.assertIsNone(url)

    def test_resolve_drive_file_grant_target_url_hides_raw_private_file_fallback(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "File":
                    self.assertEqual(filters, "FILE-EMP-1")
                    self.assertEqual(fieldname, "file_url")
                    return "/private/files/secret.pdf"
                return None

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: lambda **kwargs: {"url": ""}

            target_url = file_access._resolve_drive_file_grant_target_url(
                drive_file_id="DRIVE-FILE-1",
                file_id="FILE-EMP-1",
            )

        self.assertIsNone(target_url)

    def test_resolve_drive_file_grant_target_url_keeps_public_fallback(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "File":
                    self.assertEqual(filters, "FILE-EMP-1")
                    self.assertEqual(fieldname, "file_url")
                    return "/files/public-brochure.pdf"
                return None

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: lambda **kwargs: {"url": ""}

            target_url = file_access._resolve_drive_file_grant_target_url(
                drive_file_id="DRIVE-FILE-1",
                file_id="FILE-EMP-1",
            )

        self.assertEqual(target_url, "/files/public-brochure.pdf")

    def test_resolve_employee_file_open_url_keeps_requested_derivative_role(self):
        with _file_access_module() as (file_access, _frappe):
            url = file_access.resolve_employee_file_open_url(
                file_name="FILE-EMP-1",
                file_url="/private/files/employee.png",
                context_doctype="Employee",
                context_name="EMP-0001",
                derivative_role="thumb",
            )

        parsed = urlparse(url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_employee_file")
        self.assertEqual((query.get("derivative_role") or [None])[0], "thumb")

    def test_resolve_drive_file_grant_target_url_strict_derivative_skips_public_original_fallback(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "File":
                    self.assertEqual(filters, "FILE-EMP-1")
                    self.assertEqual(fieldname, "file_url")
                    return "/files/public-brochure.pdf"
                return None

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: lambda **kwargs: {"url": ""}

            target_url = file_access._resolve_drive_file_grant_target_url(
                drive_file_id="DRIVE-FILE-1",
                file_id="FILE-EMP-1",
                prefer_preview=True,
                derivative_role="thumb",
                strict_derivative=True,
            )

        self.assertIsNone(target_url)

    def test_resolve_cached_thumbnail_target_url_ignores_unsafe_cached_private_path(self):
        with _file_access_module() as (file_access, frappe):
            cache_writes: list[tuple[str, str, int | None]] = []

            class _FakeCache:
                def get_value(self, key):
                    return "/private/files/stale-thumb.webp"

                def set_value(self, key, value, expires_in_sec=None):
                    cache_writes.append((key, value, expires_in_sec))

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "Drive File")
                self.assertEqual(filters, "DRIVE-FILE-1")
                self.assertEqual(fieldname, ["name", "current_version"])
                self.assertTrue(as_dict)
                return {"name": "DRIVE-FILE-1", "current_version": "VER-1"}

            frappe.db.get_value = fake_get_value
            frappe.cache = lambda: _FakeCache()
            file_access._resolve_drive_file_grant_target_url = lambda **kwargs: "https://thumb.example.com/fresh.webp"

            target_url = file_access._resolve_cached_thumbnail_target_url(
                drive_file_id="DRIVE-FILE-1",
                file_id="FILE-EMP-1",
                surface_parts=["org_communication", "COMM-1", "row-1"],
            )

        self.assertEqual(target_url, "https://thumb.example.com/fresh.webp")
        self.assertEqual(len(cache_writes), 1)
        self.assertEqual(cache_writes[0][1], "https://thumb.example.com/fresh.webp")

    def test_request_org_communication_attachment_grant_prefers_communications_wrapper(self):
        with _file_access_module() as (file_access, _frappe):
            grant_calls: list[tuple[str, dict]] = []
            generic_calls: list[tuple[str, dict]] = []

            def fake_communications_loader(attribute):
                def _grant(**kwargs):
                    grant_calls.append((attribute, kwargs))
                    return {"url": "https://preview.example.com/policy.png"}

                return _grant

            def fake_generic_loader(attribute):
                def _grant(**kwargs):
                    generic_calls.append((attribute, kwargs))
                    return {"url": "https://generic.example.com/policy.png"}

                return _grant

            file_access._load_drive_communications_callable = fake_communications_loader
            file_access._load_drive_access_callable = fake_generic_loader

            grant = file_access._request_org_communication_attachment_grant(
                method_name="issue_org_communication_attachment_preview_grant",
                org_communication="COMM-0001",
                row_name="row-001",
                drive_file_id="DRIVE-FILE-1",
                derivative_role="thumb",
            )

        self.assertEqual(grant, {"url": "https://preview.example.com/policy.png"})
        self.assertEqual(
            grant_calls,
            [
                (
                    "issue_org_communication_attachment_preview_grant",
                    {
                        "org_communication": "COMM-0001",
                        "row_name": "row-001",
                        "derivative_role": "thumb",
                    },
                )
            ],
        )
        self.assertEqual(generic_calls, [])

    def test_resolve_org_communication_attachment_grant_target_url_uses_preview_wrapper_when_ready(self):
        with _file_access_module() as (file_access, frappe):
            grant_calls: list[tuple[str, dict]] = []

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "Drive File":
                    self.assertEqual(filters, "DRIVE-FILE-1")
                    self.assertEqual(fieldname, "preview_status")
                    return "ready"
                self.fail(f"Unexpected get_value call: {(doctype, filters, fieldname, as_dict)}")

            def fake_communications_loader(attribute):
                def _grant(**kwargs):
                    grant_calls.append((attribute, kwargs))
                    return {"url": "https://preview.example.com/policy.pdf"}

                return _grant

            frappe.db.get_value = fake_get_value
            file_access._load_drive_communications_callable = fake_communications_loader
            file_access._load_drive_access_callable = lambda attribute: self.fail(
                f"Generic Drive grant path should not be used: {attribute}"
            )

            target_url = file_access._resolve_org_communication_attachment_grant_target_url(
                org_communication="COMM-0001",
                row_name="row-001",
                drive_file_id="DRIVE-FILE-1",
                file_id="FILE-0001",
                prefer_preview=True,
            )

        self.assertEqual(target_url, "https://preview.example.com/policy.pdf")
        self.assertEqual(
            grant_calls,
            [
                (
                    "issue_org_communication_attachment_preview_grant",
                    {
                        "org_communication": "COMM-0001",
                        "row_name": "row-001",
                    },
                )
            ],
        )

    def test_thumbnail_academic_file_fails_closed_without_ready_thumb_target(self):
        with _file_access_module() as (file_access, frappe):
            thumbnail_requests: list[dict] = []
            frappe.local.response = {}
            file_access._resolve_authorized_academic_file = lambda **kwargs: {
                "name": "FILE-ACADEMIC-1",
                "file_url": "/private/files/material.png",
                "file_name": "material.png",
                "is_private": 1,
            }
            file_access._resolve_drive_file_delivery_row = lambda file_name: {
                "name": "DRIVE-FILE-1",
                "preview_status": "ready",
                "current_version": "VER-1",
            }

            def fake_resolve_cached_thumbnail_target_url(**kwargs):
                thumbnail_requests.append(kwargs)
                return None

            file_access._resolve_cached_thumbnail_target_url = fake_resolve_cached_thumbnail_target_url

            with self.assertRaises(frappe.DoesNotExistError):
                file_access.thumbnail_academic_file(
                    file="FILE-ACADEMIC-1",
                    context_doctype="Material Placement",
                    context_name="MAT-PLC-0001",
                )

        self.assertEqual(
            thumbnail_requests,
            [
                {
                    "drive_file_id": "DRIVE-FILE-1",
                    "file_id": "FILE-ACADEMIC-1",
                    "surface_parts": [
                        "academic",
                        "Material Placement",
                        "MAT-PLC-0001",
                        None,
                        None,
                        "FILE-ACADEMIC-1",
                    ],
                    "strict_derivative": True,
                }
            ],
        )
        self.assertEqual(frappe.local.response, {})

    def test_resolve_drive_download_grant_url_returns_signed_url(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "Drive File")
                self.assertEqual(filters, {"file": "FILE-EMP-1"})
                self.assertEqual(fieldname, ["name", "preview_status", "current_version"])
                self.assertTrue(as_dict)
                return {"name": "DRIVE-FILE-1", "preview_status": None, "current_version": "VER-1"}

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: {"url": f"https://signed.example.com/{drive_file_id}"}
            )

            target_url = file_access._resolve_drive_download_grant_url("FILE-EMP-1")

        self.assertEqual(target_url, "https://signed.example.com/DRIVE-FILE-1")

    def test_resolve_drive_download_grant_url_hides_raw_private_target(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "Drive File")
                self.assertEqual(filters, {"file": "FILE-EMP-1"})
                self.assertEqual(fieldname, ["name", "preview_status", "current_version"])
                self.assertTrue(as_dict)
                return {"name": "DRIVE-FILE-1", "preview_status": None, "current_version": "VER-1"}

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: {"url": "/private/files/ifitwala_drive/files/aa/bb/document.pdf"}
            )

            target_url = file_access._resolve_drive_download_grant_url("FILE-EMP-1")

        self.assertIsNone(target_url)

    def test_resolve_drive_preview_grant_url_hides_raw_private_target(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "Drive File")
                self.assertEqual(filters, {"file": "FILE-EMP-1"})
                self.assertEqual(fieldname, ["name", "preview_status", "current_version"])
                self.assertTrue(as_dict)
                return {"name": "DRIVE-FILE-1", "preview_status": "ready", "current_version": "VER-1"}

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: {"url": "/private/files/ifitwala_drive/derivatives/aa/bb/pdf_page_1.png"}
            )

            target_url = file_access._resolve_drive_preview_grant_url("FILE-EMP-1")

        self.assertIsNone(target_url)

    def test_download_employee_file_redirects_to_drive_grant_when_local_bytes_missing(self):
        with _file_access_module() as (file_access, frappe):
            file_access.has_active_employee_profile = lambda **kwargs: True
            frappe.session.user = "staff@example.com"
            frappe.local.response = {}
            frappe.db.exists = lambda doctype, name=None: doctype == "Employee" and name == "EMP-0001"

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "Drive File":
                    self.assertEqual(filters, {"file": "FILE-EMP-1"})
                    self.assertEqual(fieldname, ["name", "preview_status", "current_version"])
                    self.assertTrue(as_dict)
                    return {"name": "DRIVE-FILE-1", "preview_status": None, "current_version": "VER-1"}
                return None

            frappe.db.get_value = fake_get_value
            file_access._resolve_any_file_row = lambda file_name: {
                "name": file_name,
                "file_url": "/private/files/ifitwala_drive/files/aa/bb/thumb_employee.webp",
                "file_name": "thumb_employee.webp",
                "is_private": 1,
                "attached_to_doctype": "Employee",
                "attached_to_name": "EMP-0001",
            }
            file_access._read_file_bytes = lambda file_row: None
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: {"url": "https://signed.example.com/thumb_employee.webp"}
            )

            file_access.download_employee_file(
                file="FILE-EMP-1",
                context_doctype="Employee",
                context_name="EMP-0001",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://signed.example.com/thumb_employee.webp",
        )

    def test_download_employee_file_still_enforces_employee_access_before_drive_grant(self):
        with _file_access_module() as (file_access, frappe):
            drive_grant_calls: list[str] = []
            file_access.has_active_employee_profile = lambda **kwargs: False
            frappe.session.user = "staff@example.com"
            frappe.local.response = {}
            frappe.db.exists = lambda doctype, name=None: doctype == "Employee" and name == "EMP-0001"

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "Drive File":
                    return "DRIVE-FILE-1"
                return None

            frappe.db.get_value = fake_get_value
            file_access._resolve_any_file_row = lambda file_name: {
                "name": file_name,
                "file_url": "/private/files/ifitwala_drive/files/aa/bb/thumb_employee.webp",
                "file_name": "thumb_employee.webp",
                "is_private": 1,
                "attached_to_doctype": "Employee",
                "attached_to_name": "EMP-0001",
            }
            file_access._read_file_bytes = lambda file_row: None
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: drive_grant_calls.append(drive_file_id) or {"url": "https://signed.example.com/x"}
            )

            with self.assertRaises(frappe.PermissionError):
                file_access.download_employee_file(
                    file="FILE-EMP-1",
                    context_doctype="Employee",
                    context_name="EMP-0001",
                )

        self.assertEqual(drive_grant_calls, [])
