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
    org_comm_utils.expand_employee_visibility_context = lambda employee, roles: employee or {}

    curriculum_materials = ModuleType("ifitwala_ed.curriculum.materials")
    curriculum_materials.user_can_read_material_anchor = lambda *args, **kwargs: False
    curriculum_materials.user_can_read_supporting_material = lambda *args, **kwargs: False

    routing_policy = ModuleType("ifitwala_ed.routing.policy")
    routing_policy.has_active_employee_profile = lambda **kwargs: True

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.admission.access": admission_access,
            "ifitwala_ed.admission.admission_utils": admission_utils,
            "ifitwala_ed.api.org_comm_utils": org_comm_utils,
            "ifitwala_ed.curriculum.materials": curriculum_materials,
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
    def test_resolve_admissions_file_open_url_prefers_drive_identity_without_file_lookup(self):
        with _file_access_module() as (file_access, frappe):
            frappe.db.get_value = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("unexpected file lookup")
            )

            url = file_access.resolve_admissions_file_open_url(
                file_name=None,
                file_url=None,
                drive_file_id="DRIVE-FILE-1",
                canonical_ref="drv:ORG-1:DRIVE-FILE-1",
                context_doctype="Student Applicant",
                context_name="APPL-0001",
            )

        parsed = urlparse(url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_admissions_file")
        self.assertEqual((query.get("drive_file_id") or [None])[0], "DRIVE-FILE-1")
        self.assertEqual((query.get("context_name") or [None])[0], "APPL-0001")

    def test_resolve_admissions_file_thumbnail_url_requires_ready_thumbnail(self):
        with _file_access_module() as (file_access, _frappe):
            ready_url = file_access.resolve_admissions_file_thumbnail_url(
                file_name=None,
                file_url=None,
                drive_file_id="DRIVE-FILE-2",
                canonical_ref="drv:ORG-1:DRIVE-FILE-2",
                context_doctype="Student Applicant",
                context_name="APPL-0001",
                thumbnail_ready=True,
            )
            missing_url = file_access.resolve_admissions_file_thumbnail_url(
                file_name=None,
                file_url=None,
                drive_file_id="DRIVE-FILE-2",
                canonical_ref="drv:ORG-1:DRIVE-FILE-2",
                context_doctype="Student Applicant",
                context_name="APPL-0001",
                thumbnail_ready=False,
            )

        parsed = urlparse(ready_url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.thumbnail_admissions_file")
        self.assertEqual((query.get("drive_file_id") or [None])[0], "DRIVE-FILE-2")
        self.assertIsNone(missing_url)

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

    def test_resolve_drive_file_grant_target_url_keeps_local_private_grant_target_for_delivery(self):
        with _file_access_module() as (file_access, frappe):
            file_access._load_drive_access_callable = lambda attribute: (
                lambda **kwargs: {"url": "/private/files/secret.pdf"}
            )

            target_url = file_access._resolve_drive_file_grant_target_url(
                drive_file_id="DRIVE-FILE-1",
                file_id="FILE-EMP-1",
            )

        self.assertEqual(target_url, "/private/files/secret.pdf")

    def test_resolve_drive_file_grant_target_url_returns_none_without_safe_grant(self):
        with _file_access_module() as (file_access, frappe):
            file_access._load_drive_access_callable = lambda attribute: lambda **kwargs: {"url": ""}

            target_url = file_access._resolve_drive_file_grant_target_url(
                drive_file_id="DRIVE-FILE-1",
                file_id="FILE-EMP-1",
            )

        self.assertIsNone(target_url)

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

    def test_resolve_employee_file_open_url_prefers_drive_identity_without_file_lookup(self):
        with _file_access_module() as (file_access, frappe):
            frappe.db.get_value = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("unexpected compatibility file lookup")
            )

            url = file_access.resolve_employee_file_open_url(
                file_name=None,
                file_url=None,
                drive_file_id="DRIVE-FILE-EMP-1",
                canonical_ref="drv:ORG-1:DRIVE-FILE-EMP-1",
                context_doctype="Employee",
                context_name="EMP-0001",
                derivative_role="card",
            )

        parsed = urlparse(url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/api/method/ifitwala_ed.api.file_access.download_employee_file")
        self.assertEqual((query.get("drive_file_id") or [None])[0], "DRIVE-FILE-EMP-1")
        self.assertEqual((query.get("context_name") or [None])[0], "EMP-0001")
        self.assertEqual((query.get("derivative_role") or [None])[0], "card")

    def test_resolve_drive_file_grant_target_url_strict_derivative_returns_none_without_safe_grant(self):
        with _file_access_module() as (file_access, frappe):
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

    def test_preview_org_communication_attachment_works_without_compatibility_file_on_binding(self):
        with _file_access_module() as (file_access, frappe):
            frappe.session.user = "staff@example.com"
            frappe.local.response = {}
            frappe.get_roles = lambda user: ["Employee"]
            file_access.check_audience_match = lambda *args, **kwargs: True

            attachment_row = SimpleNamespace(
                name="row-001",
                external_url="",
                file="/private/files/ifitwala_drive/files/aa/bb/policy.pdf",
            )
            doc = SimpleNamespace(name="COMM-0001", attachments=[attachment_row])
            doc.get = lambda fieldname, default=None: getattr(doc, fieldname, default)
            frappe.get_doc = lambda doctype, name: doc

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "Employee":
                    return {"name": "EMP-0001", "school": "SCHOOL-1", "organization": "ORG-1"}
                if doctype == "Drive Binding":
                    return {"drive_file": "DRIVE-FILE-1", "file": ""}
                if doctype == "Drive File" and filters == "DRIVE-FILE-1" and fieldname == "preview_status":
                    return "ready"
                return None

            frappe.db.get_value = fake_get_value
            file_access._load_drive_communications_callable = lambda attribute: (
                lambda **kwargs: {"url": "https://preview.example.com/policy.pdf"}
            )

            file_access.preview_org_communication_attachment(
                org_communication="COMM-0001",
                row_name="row-001",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://preview.example.com/policy.pdf",
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
                    "target_resolver": None,
                }
            ],
        )
        self.assertEqual(frappe.local.response, {})

    def test_download_academic_file_accepts_local_drive_delivery_target(self):
        with _file_access_module() as (file_access, frappe):
            delivery_requests: list[dict] = []
            frappe.local.response = {}
            file_access._resolve_authorized_academic_file = lambda **kwargs: {
                "name": "FILE-ACADEMIC-1",
                "file_url": "/private/files/student.webp",
                "file_name": "student.webp",
                "is_private": 1,
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
            }
            file_access._resolve_drive_download_grant_url = lambda file_name=None, **kwargs: (
                "/private/files/ifitwala_drive/files/aa/bb/student.webp"
            )
            file_access._respond_with_delivery_target = lambda **kwargs: delivery_requests.append(kwargs) or True

            file_access.download_academic_file(
                file="FILE-ACADEMIC-1",
                context_doctype="Student",
                context_name="STU-0001",
            )

        self.assertEqual(
            delivery_requests,
            [{"target_url": "/private/files/ifitwala_drive/files/aa/bb/student.webp"}],
        )

    def test_preview_academic_file_accepts_local_drive_delivery_target(self):
        with _file_access_module() as (file_access, frappe):
            delivery_requests: list[dict] = []
            frappe.local.response = {}
            file_access._resolve_authorized_academic_file = lambda **kwargs: {
                "name": "FILE-ACADEMIC-1",
                "file_url": "/private/files/student.webp",
                "file_name": "student.webp",
                "is_private": 1,
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
            }
            file_access._resolve_drive_preview_grant_url = lambda file_name=None, **kwargs: (
                "/private/files/ifitwala_drive/files/aa/bb/student.webp"
            )
            file_access._respond_with_delivery_target = lambda **kwargs: delivery_requests.append(kwargs) or True

            file_access.preview_academic_file(
                file="FILE-ACADEMIC-1",
                context_doctype="Student",
                context_name="STU-0001",
            )

        self.assertEqual(
            delivery_requests,
            [{"target_url": "/private/files/ifitwala_drive/files/aa/bb/student.webp"}],
        )

    def test_thumbnail_academic_file_accepts_local_drive_delivery_target(self):
        with _file_access_module() as (file_access, frappe):
            delivery_requests: list[dict] = []
            frappe.local.response = {}
            file_access._resolve_authorized_academic_file = lambda **kwargs: {
                "name": "FILE-ACADEMIC-1",
                "file_url": "/private/files/student.webp",
                "file_name": "student.webp",
                "is_private": 1,
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
            }
            file_access._resolve_drive_file_delivery_row = lambda file_name: {
                "name": "DRIVE-FILE-1",
                "preview_status": "ready",
                "current_version": "VER-1",
            }
            file_access._resolve_cached_thumbnail_target_url = lambda **kwargs: (
                "/private/files/ifitwala_drive/derivatives/aa/bb/student_thumb.webp"
            )
            file_access._respond_with_delivery_target = lambda **kwargs: delivery_requests.append(kwargs) or True

            file_access.thumbnail_academic_file(
                file="FILE-ACADEMIC-1",
                context_doctype="Student",
                context_name="STU-0001",
            )

        self.assertEqual(
            delivery_requests,
            [
                {
                    "target_url": "/private/files/ifitwala_drive/derivatives/aa/bb/student_thumb.webp",
                    "cache_headers": True,
                }
            ],
        )

    def test_download_admissions_file_accepts_local_drive_delivery_target(self):
        with _file_access_module() as (file_access, frappe):
            delivery_requests: list[dict] = []
            frappe.local.response = {}
            frappe.session.user = "staff@example.com"
            file_access._resolve_authorized_admissions_file_target = lambda **kwargs: (
                {
                    "name": "FILE-ADM-1",
                    "file_url": "/private/files/admissions.pdf",
                    "file_name": "admissions.pdf",
                    "is_private": 1,
                },
                {"name": "DRIVE-FILE-ADM-1"},
            )
            file_access._resolve_drive_download_grant_url = lambda *args, **kwargs: (
                "/private/files/ifitwala_drive/files/aa/bb/admissions.pdf"
            )
            file_access._respond_with_delivery_target = lambda **kwargs: delivery_requests.append(kwargs) or True

            file_access.download_admissions_file(
                file="FILE-ADM-1",
                context_doctype="Student Applicant",
                context_name="APPL-0001",
            )

        self.assertEqual(
            delivery_requests,
            [{"target_url": "/private/files/ifitwala_drive/files/aa/bb/admissions.pdf"}],
        )

    def test_thumbnail_admissions_file_accepts_local_drive_delivery_target(self):
        with _file_access_module() as (file_access, frappe):
            delivery_requests: list[dict] = []
            frappe.local.response = {}
            frappe.session.user = "staff@example.com"
            file_access._resolve_authorized_admissions_file_target = lambda **kwargs: (
                {
                    "name": "FILE-ADM-1",
                    "file_url": "/private/files/admissions.png",
                    "file_name": "admissions.png",
                    "is_private": 1,
                },
                {"name": "DRIVE-FILE-ADM-1", "file": "FILE-ADM-1"},
            )
            file_access._resolve_cached_thumbnail_target_url = lambda **kwargs: (
                "/private/files/ifitwala_drive/derivatives/aa/bb/admissions_thumb.png"
            )
            file_access._respond_with_delivery_target = lambda **kwargs: delivery_requests.append(kwargs) or True

            file_access.thumbnail_admissions_file(
                file="FILE-ADM-1",
                context_doctype="Student Applicant",
                context_name="APPL-0001",
            )

        self.assertEqual(
            delivery_requests,
            [
                {
                    "target_url": "/private/files/ifitwala_drive/derivatives/aa/bb/admissions_thumb.png",
                    "cache_headers": True,
                }
            ],
        )

    def test_download_guardian_file_accepts_local_drive_delivery_target(self):
        with _file_access_module() as (file_access, frappe):
            delivery_requests: list[dict] = []
            frappe.local.response = {}
            frappe.session.user = "guardian@example.com"
            file_access._resolve_any_file_row = lambda file_name: {
                "name": file_name,
                "file_url": "/private/files/guardian.webp",
                "file_name": "guardian.webp",
                "is_private": 1,
                "attached_to_doctype": "Guardian",
                "attached_to_name": "GRD-0001",
            }
            file_access._resolve_guardian_from_file = lambda file_row: "GRD-0001"
            file_access._assert_guardian_file_access = lambda **kwargs: None
            file_access._resolve_drive_download_grant_url = lambda *args, **kwargs: (
                "/private/files/ifitwala_drive/files/aa/bb/guardian.webp"
            )
            file_access._respond_with_delivery_target = lambda **kwargs: delivery_requests.append(kwargs) or True

            file_access.download_guardian_file(
                file="FILE-GRD-1",
                context_doctype="Guardian",
                context_name="GRD-0001",
            )

        self.assertEqual(
            delivery_requests,
            [{"target_url": "/private/files/ifitwala_drive/files/aa/bb/guardian.webp"}],
        )

    def test_download_guardian_file_uses_guardian_image_preview_grant_for_profile_images(self):
        with _file_access_module() as (file_access, frappe):
            frappe.local.response = {}
            frappe.session.user = "guardian@example.com"
            file_access._resolve_any_file_row = lambda file_name: {
                "name": file_name,
                "file_url": "/private/files/guardian_thumb.webp",
                "file_name": "guardian_thumb.webp",
                "is_private": 1,
                "attached_to_doctype": "Guardian",
                "attached_to_name": "GRD-0001",
                "attached_to_field": "guardian_image",
            }
            file_access.get_drive_file_for_file = lambda file_name, **kwargs: {
                "name": "DRIVE-GRD-1",
                "owner_doctype": "Guardian",
                "owner_name": "GRD-0001",
                "primary_subject_type": "Guardian",
                "primary_subject_id": "GRD-0001",
                "purpose": "guardian_profile_display",
                "slot": "profile_image",
            }
            file_access._load_drive_media_callable = lambda attribute: (
                self.assertEqual(attribute, "issue_guardian_image_preview_grant")
                or (
                    lambda guardian, file_id, derivative_role=None: {"url": "https://signed.example.com/guardian-thumb"}
                )
            )
            file_access._load_drive_access_callable = lambda attribute: self.fail(
                "generic drive grant path should not be used for guardian profile images"
            )
            frappe.db.get_value = lambda doctype, filters, fieldname=None, as_dict=False: (
                "GRD-0001" if doctype == "Guardian" else None
            )

            file_access.download_guardian_file(
                file="FILE-GRD-IMG-1",
                context_doctype="Guardian",
                context_name="GRD-0001",
                derivative_role="thumb",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(frappe.local.response.get("location"), "https://signed.example.com/guardian-thumb")

    def test_download_academic_file_uses_student_image_preview_grant_for_profile_images(self):
        with _file_access_module() as (file_access, frappe):
            frappe.local.response = {}
            frappe.session.user = "staff@example.com"
            file_access._resolve_authorized_academic_file = lambda **kwargs: {
                "name": "FILE-STU-IMG-1",
                "file_url": "/private/files/student_thumb.webp",
                "file_name": "student_thumb.webp",
                "is_private": 1,
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
                "attached_to_field": "student_image",
            }
            file_access._resolve_any_file_row = lambda file_name: {
                "name": file_name,
                "file_url": "/private/files/student_thumb.webp",
                "file_name": "student_thumb.webp",
                "is_private": 1,
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
                "attached_to_field": "student_image",
            }
            file_access.get_drive_file_for_file = lambda file_name, **kwargs: {
                "name": "DRIVE-STU-1",
                "owner_doctype": "Student",
                "owner_name": "STU-0001",
                "primary_subject_type": "Student",
                "primary_subject_id": "STU-0001",
                "purpose": "student_profile_display",
                "slot": "profile_image",
                "school": "SCH-0001",
            }
            file_access._assert_internal_student_access = lambda **kwargs: None
            file_access._load_drive_media_callable = lambda attribute: (
                self.assertEqual(attribute, "issue_student_image_preview_grant")
                or (lambda student, file_id, derivative_role=None: {"url": "https://signed.example.com/student-thumb"})
            )
            file_access._load_drive_access_callable = lambda attribute: self.fail(
                "generic drive grant path should not be used for student profile images"
            )

            file_access.download_academic_file(
                file="FILE-STU-IMG-1",
                context_doctype="Student",
                context_name="STU-0001",
                derivative_role="thumb",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(frappe.local.response.get("location"), "https://signed.example.com/student-thumb")

    def test_download_academic_file_falls_back_to_current_student_profile_image_when_old_file_binding_rotated(self):
        with _file_access_module() as (file_access, frappe):
            frappe.local.response = {}
            frappe.session.user = "staff@example.com"
            file_access._resolve_authorized_academic_file = lambda **kwargs: {
                "name": "FILE-STALE-STU-IMG",
                "file_url": "/private/files/student_old.webp",
                "file_name": "student_old.webp",
                "is_private": 1,
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
                "attached_to_field": "student_image",
            }
            file_access._resolve_student_profile_image_access = lambda **kwargs: None
            file_access._resolve_current_student_profile_drive_file = lambda student: {
                "name": "DRIVE-STU-CURRENT",
                "file": "FILE-CURRENT-STU-IMG",
            }
            file_access._resolve_student_profile_image_access_from_drive_file = lambda **kwargs: {
                "file_row": {
                    "name": "FILE-CURRENT-STU-IMG",
                    "file_url": "/private/files/student_current.webp",
                    "file_name": "student_current.webp",
                    "is_private": 1,
                    "attached_to_doctype": "Student",
                    "attached_to_name": "STU-0001",
                    "attached_to_field": "student_image",
                },
                "file_student": "STU-0001",
                "school": "SCH-0001",
                "drive_file_id": "DRIVE-STU-CURRENT",
            }
            file_access._respond_with_delivery_target = lambda **kwargs: (
                frappe.local.response.update({"type": "redirect", "location": kwargs["target_url"]}) or True
            )

            def fake_student_target(**kwargs):
                self.assertEqual(kwargs["file_id"], "FILE-CURRENT-STU-IMG")
                self.assertEqual(kwargs["drive_file_id"], "DRIVE-STU-CURRENT")
                self.assertEqual(kwargs["student"], "STU-0001")
                self.assertEqual(kwargs["derivative_role"], "thumb")
                self.assertTrue(kwargs["prefer_preview"])
                return "https://signed.example.com/current-student-thumb"

            file_access._resolve_student_image_grant_target_url = fake_student_target

            file_access.download_academic_file(
                file="FILE-STALE-STU-IMG",
                context_doctype="Student",
                context_name="STU-0001",
                derivative_role="thumb",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://signed.example.com/current-student-thumb",
        )

    def test_open_public_website_media_accepts_local_drive_delivery_target(self):
        with _file_access_module() as (file_access, frappe):
            delivery_requests: list[dict] = []
            frappe.local.response = {}
            file_access._resolve_public_website_media_row = lambda file_name: {
                "name": file_name,
                "file_url": "/private/files/logo.webp",
                "file_name": "logo.webp",
                "is_private": 1,
            }
            file_access._assert_public_website_media_visible = lambda file_row: None
            file_access._resolve_public_website_media_grant_url = lambda file_name: (
                "/private/files/ifitwala_drive/files/aa/bb/logo.webp"
            )
            file_access._respond_with_delivery_target = lambda **kwargs: delivery_requests.append(kwargs) or True

            file_access.open_public_website_media(file="FILE-PUBLIC-1")

        self.assertEqual(
            delivery_requests,
            [{"target_url": "/private/files/ifitwala_drive/files/aa/bb/logo.webp"}],
        )

    def test_resolve_supporting_material_grant_target_url_keeps_local_private_target_for_delivery(self):
        with _file_access_module() as (file_access, frappe):
            frappe.db.get_value = lambda *args, **kwargs: "ready"
            file_access._request_supporting_material_grant = lambda **kwargs: {
                "url": "/private/files/ifitwala_drive/files/aa/bb/material.pdf"
            }

            target_url = file_access._resolve_supporting_material_grant_target_url(
                material="MAT-0001",
                placement=None,
                drive_file_id="DRIVE-FILE-MAT-1",
                file_id="FILE-MAT-1",
                prefer_preview=True,
            )

        self.assertEqual(target_url, "/private/files/ifitwala_drive/files/aa/bb/material.pdf")

    def test_resolve_drive_download_grant_url_returns_signed_url(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "Drive File")
                self.assertEqual(filters, {"file": "FILE-EMP-1"})
                self.assertEqual(
                    fieldname,
                    [
                        "name",
                        "file",
                        "canonical_ref",
                        "preview_status",
                        "current_version",
                        "owner_doctype",
                        "owner_name",
                        "primary_subject_type",
                        "primary_subject_id",
                        "attached_doctype",
                        "attached_name",
                        "purpose",
                        "slot",
                    ],
                )
                self.assertTrue(as_dict)
                return {"name": "DRIVE-FILE-1", "preview_status": None, "current_version": "VER-1"}

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: {"url": f"https://signed.example.com/{drive_file_id}"}
            )

            target_url = file_access._resolve_drive_download_grant_url("FILE-EMP-1")

        self.assertEqual(target_url, "https://signed.example.com/DRIVE-FILE-1")

    def test_resolve_drive_download_grant_url_keeps_local_private_target_for_delivery(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "Drive File")
                self.assertEqual(filters, {"file": "FILE-EMP-1"})
                self.assertEqual(
                    fieldname,
                    [
                        "name",
                        "file",
                        "canonical_ref",
                        "preview_status",
                        "current_version",
                        "owner_doctype",
                        "owner_name",
                        "primary_subject_type",
                        "primary_subject_id",
                        "attached_doctype",
                        "attached_name",
                        "purpose",
                        "slot",
                    ],
                )
                self.assertTrue(as_dict)
                return {"name": "DRIVE-FILE-1", "preview_status": None, "current_version": "VER-1"}

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: {"url": "/private/files/ifitwala_drive/files/aa/bb/document.pdf"}
            )

            target_url = file_access._resolve_drive_download_grant_url("FILE-EMP-1")

        self.assertEqual(target_url, "/private/files/ifitwala_drive/files/aa/bb/document.pdf")

    def test_resolve_drive_preview_grant_url_keeps_local_private_target_for_delivery(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "Drive File")
                self.assertEqual(filters, {"file": "FILE-EMP-1"})
                self.assertEqual(
                    fieldname,
                    [
                        "name",
                        "file",
                        "canonical_ref",
                        "preview_status",
                        "current_version",
                        "owner_doctype",
                        "owner_name",
                        "primary_subject_type",
                        "primary_subject_id",
                        "attached_doctype",
                        "attached_name",
                        "purpose",
                        "slot",
                    ],
                )
                self.assertTrue(as_dict)
                return {"name": "DRIVE-FILE-1", "preview_status": "ready", "current_version": "VER-1"}

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: {"url": "/private/files/ifitwala_drive/derivatives/aa/bb/pdf_page_1.png"}
            )

            target_url = file_access._resolve_drive_preview_grant_url("FILE-EMP-1")

        self.assertEqual(target_url, "/private/files/ifitwala_drive/derivatives/aa/bb/pdf_page_1.png")

    def test_download_employee_file_redirects_to_employee_image_preview_grant_for_private_file(self):
        with _file_access_module() as (file_access, frappe):
            file_access.has_active_employee_profile = lambda **kwargs: True
            frappe.session.user = "staff@example.com"
            frappe.local.response = {}
            frappe.db.exists = lambda doctype, name=None: doctype == "Employee" and name == "EMP-0001"
            file_access.get_drive_file_for_file = lambda file_name, **kwargs: {
                "name": "DRIVE-FILE-1",
                "owner_doctype": "Employee",
                "owner_name": "EMP-0001",
                "primary_subject_type": "Employee",
                "primary_subject_id": "EMP-0001",
                "purpose": "employee_profile_display",
                "slot": "profile_image",
            }
            file_access._resolve_any_file_row = lambda file_name: {
                "name": file_name,
                "file_url": "/private/files/ifitwala_drive/files/aa/bb/thumb_employee.webp",
                "file_name": "thumb_employee.webp",
                "is_private": 1,
                "attached_to_doctype": "Employee",
                "attached_to_name": "EMP-0001",
            }
            file_access._load_drive_media_callable = lambda attribute: (
                lambda employee, file_id: {"url": "https://signed.example.com/thumb_employee.webp"}
            )
            file_access._load_drive_access_callable = lambda attribute: self.fail(
                "generic drive grant path should not be used for employee profile images"
            )

            file_access.download_employee_file(
                file="FILE-EMP-1",
                context_doctype="Employee",
                context_name="EMP-0001",
                derivative_role="thumb",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://signed.example.com/thumb_employee.webp",
        )

    def test_download_employee_file_falls_back_to_current_governed_profile_when_requested_file_is_stale(self):
        with _file_access_module() as (file_access, frappe):
            file_access.has_active_employee_profile = lambda **kwargs: True
            frappe.session.user = "staff@example.com"
            frappe.local.response = {}
            frappe.db.exists = lambda doctype, name=None: doctype == "Employee" and name == "EMP-0001"
            file_access._resolve_employee_profile_image_access = lambda **kwargs: (_ for _ in ()).throw(
                frappe.DoesNotExistError("File not found.")
            )
            file_access.get_current_drive_file_for_slot = lambda **kwargs: {
                "name": "DRIVE-FILE-EMP-1",
                "file": "FILE-EMP-CURRENT",
                "owner_doctype": "Employee",
                "owner_name": "EMP-0001",
                "attached_doctype": "Employee",
                "attached_name": "EMP-0001",
                "primary_subject_type": "Employee",
                "primary_subject_id": "EMP-0001",
                "purpose": "employee_profile_display",
                "slot": "profile_image",
            }
            file_access._get_any_file_row = lambda file_name: {
                "name": "FILE-EMP-CURRENT",
                "file_url": "/private/files/ifitwala_drive/files/aa/bb/profile.webp",
                "file_name": "profile.webp",
                "is_private": 1,
                "attached_to_doctype": "Employee",
                "attached_to_name": "EMP-0001",
            }
            file_access._load_drive_media_callable = lambda attribute: (
                lambda employee, file_id, **kwargs: {"url": "https://signed.example.com/profile.webp"}
            )

            file_access.download_employee_file(
                file="FILE-EMP-STALE",
                context_doctype="Employee",
                context_name="EMP-0001",
                derivative_role="thumb",
            )

        self.assertEqual(frappe.local.response.get("type"), "redirect")
        self.assertEqual(
            frappe.local.response.get("location"),
            "https://signed.example.com/profile.webp",
        )

    def test_download_employee_file_still_enforces_employee_access_before_drive_grant(self):
        with _file_access_module() as (file_access, frappe):
            drive_grant_calls: list[str] = []
            file_access.has_active_employee_profile = lambda **kwargs: False
            frappe.session.user = "staff@example.com"
            frappe.local.response = {}
            frappe.db.exists = lambda doctype, name=None: doctype == "Employee" and name == "EMP-0001"
            file_access.get_drive_file_for_file = lambda file_name, **kwargs: {
                "name": "DRIVE-FILE-1",
                "owner_doctype": "Employee",
                "owner_name": "EMP-0001",
                "primary_subject_type": "Employee",
                "primary_subject_id": "EMP-0001",
                "purpose": "employee_profile_display",
                "slot": "profile_image",
            }
            file_access._resolve_any_file_row = lambda file_name: {
                "name": file_name,
                "file_url": "/private/files/ifitwala_drive/files/aa/bb/thumb_employee.webp",
                "file_name": "thumb_employee.webp",
                "is_private": 1,
                "attached_to_doctype": "Employee",
                "attached_to_name": "EMP-0001",
            }
            file_access._load_drive_media_callable = lambda attribute: (
                lambda employee, file_id: drive_grant_calls.append(file_id) or {"url": "https://signed.example.com/x"}
            )
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
