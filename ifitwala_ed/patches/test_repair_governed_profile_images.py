from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _patch_module():
    authority = ModuleType("ifitwala_ed.integrations.drive.authority")
    authority.get_current_drive_file_for_slot = lambda **kwargs: None

    content_uploads = ModuleType("ifitwala_ed.integrations.drive.content_uploads")
    content_uploads.upload_content_via_drive = lambda **kwargs: ({}, {}, None)

    image_utils = ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils._read_managed_file_bytes = lambda file_doc, **kwargs: b""
    image_utils._resolve_unique_file_doc_by_url = lambda file_url: None

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.integrations.drive.authority": authority,
            "ifitwala_ed.integrations.drive.content_uploads": content_uploads,
            "ifitwala_ed.utilities.image_utils": image_utils,
        }
    ) as frappe:
        frappe.db.table_exists = lambda doctype: doctype in {"File", "Employee", "Student", "Guardian"}
        frappe.db.exists = lambda doctype, name: True
        frappe.db.set_value = lambda *args, **kwargs: None
        frappe.get_all = lambda *args, **kwargs: []
        frappe.get_doc = lambda doctype, name: SimpleNamespace(name=name, file_url=f"/private/files/{name}.png")
        yield import_fresh("ifitwala_ed.patches.repair_governed_profile_images"), frappe


class TestRepairGovernedProfileImages(TestCase):
    def test_execute_repairs_employee_student_and_guardian_profile_images(self):
        employee_rows = [{"name": "EMP-0001", "employee_image": "/private/files/employee-one.png"}]
        student_rows = [{"name": "STU-0001", "student_image": "/private/files/student-one.png"}]
        guardian_rows = [
            {
                "name": "GRD-0001",
                "guardian_image": "/private/files/guardian-one.png",
                "organization": "ORG-0001",
            }
        ]

        def _get_all(doctype, **kwargs):
            if doctype == "Employee":
                return employee_rows
            if doctype == "Student":
                return student_rows
            if doctype == "Guardian":
                return guardian_rows
            return []

        with _patch_module() as (module, frappe):
            with (
                patch.object(module.frappe, "get_all", side_effect=_get_all) as get_all,
                patch.object(module, "_repair_profile_image_row") as repair_row,
            ):
                module.execute()

        get_all.assert_any_call(
            "Employee",
            filters={"employee_image": ["is", "set"]},
            fields=["name", "employee_image"],
            limit=100000,
        )
        get_all.assert_any_call(
            "Student",
            filters={"student_image": ["is", "set"]},
            fields=["name", "student_image"],
            limit=100000,
        )
        get_all.assert_any_call(
            "Guardian",
            filters={"guardian_image": ["is", "set"]},
            fields=["name", "guardian_image", "organization"],
            limit=100000,
        )
        repair_row.assert_any_call(doctype="Employee", row=employee_rows[0])
        repair_row.assert_any_call(doctype="Student", row=student_rows[0])
        repair_row.assert_any_call(doctype="Guardian", row=guardian_rows[0])

    def test_repair_profile_image_row_requeues_derivatives_for_current_governed_image(self):
        row = {"name": "STU-0001", "student_image": "/private/files/student-one.png"}
        current_file_doc = SimpleNamespace(
            name="FILE-STU-CURRENT",
            file_url="/private/files/student-current.png",
        )

        with _patch_module() as (module, frappe):
            with (
                patch.object(module, "_resolve_current_profile_file", return_value=current_file_doc),
                patch.object(module, "_sync_profile_field") as sync_field,
                patch.object(module, "_request_preview_derivatives") as request_derivatives,
                patch.object(
                    module,
                    "_resolve_source_file_doc",
                    side_effect=AssertionError("legacy source lookup should not run for current governed files"),
                ),
            ):
                module._repair_profile_image_row(doctype="Student", row=row)

        sync_field.assert_called_once_with(
            doctype="Student",
            name="STU-0001",
            file_url="/private/files/student-current.png",
            organization=None,
        )
        request_derivatives.assert_called_once_with(
            doctype="Student",
            name="STU-0001",
            file_id="FILE-STU-CURRENT",
        )

    def test_repair_profile_image_row_uploads_legacy_employee_image_when_governed_file_missing(self):
        row = {"name": "EMP-0001", "employee_image": "/private/files/employee-one.png"}
        source_file_doc = SimpleNamespace(name="FILE-EMP-LEGACY", file_url="/private/files/employee-one.png")
        uploaded_file_doc = SimpleNamespace(
            name="FILE-EMP-CURRENT",
            file_url="/private/files/employee-current.png",
        )

        with _patch_module() as (module, frappe):
            with (
                patch.object(module, "_resolve_current_profile_file", return_value=None),
                patch.object(module, "_resolve_source_file_doc", return_value=source_file_doc) as resolve_source,
                patch.object(module, "_upload_legacy_profile_image", return_value=uploaded_file_doc) as upload_legacy,
                patch.object(module, "_request_preview_derivatives") as request_derivatives,
            ):
                module._repair_profile_image_row(doctype="Employee", row=row)

        resolve_source.assert_called_once_with(
            doctype="Employee",
            name="EMP-0001",
            fieldname="employee_image",
            original_url="/private/files/employee-one.png",
        )
        upload_legacy.assert_called_once_with(
            doctype="Employee",
            name="EMP-0001",
            source_file_doc=source_file_doc,
            organization=None,
        )
        request_derivatives.assert_called_once_with(
            doctype="Employee",
            name="EMP-0001",
            file_id="FILE-EMP-CURRENT",
        )
