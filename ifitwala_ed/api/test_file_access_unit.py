from __future__ import annotations

import importlib
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

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
    def test_resolve_drive_download_grant_url_returns_signed_url(self):
        with _file_access_module() as (file_access, frappe):

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                self.assertEqual(doctype, "Drive File")
                self.assertEqual(filters, {"file": "FILE-EMP-1"})
                self.assertEqual(fieldname, "name")
                return "DRIVE-FILE-1"

            frappe.db.get_value = fake_get_value
            file_access._load_drive_access_callable = lambda attribute: (
                lambda drive_file_id: {"url": f"https://signed.example.com/{drive_file_id}"}
            )

            target_url = file_access._resolve_drive_download_grant_url("FILE-EMP-1")

        self.assertEqual(target_url, "https://signed.example.com/DRIVE-FILE-1")

    def test_download_employee_file_redirects_to_drive_grant_when_local_bytes_missing(self):
        with _file_access_module() as (file_access, frappe):
            file_access.has_active_employee_profile = lambda **kwargs: True
            frappe.session.user = "staff@example.com"
            frappe.local.response = {}
            frappe.db.exists = lambda doctype, name=None: doctype == "Employee" and name == "EMP-0001"

            def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
                if doctype == "Drive File":
                    self.assertEqual(filters, {"file": "FILE-EMP-1"})
                    self.assertEqual(fieldname, "name")
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
