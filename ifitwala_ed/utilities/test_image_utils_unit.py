from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _image_utils_module():
    file_access = ModuleType("ifitwala_ed.api.file_access")
    file_access.resolve_employee_file_open_url = lambda **kwargs: (
        "/api/method/ifitwala_ed.api.file_access.download_employee_file"
        f"?file={kwargs.get('file_name')}&context_doctype={kwargs.get('context_doctype')}"
        f"&context_name={kwargs.get('context_name')}&derivative_role={kwargs.get('derivative_role')}"
    )
    file_access.resolve_guardian_file_open_url = lambda **kwargs: None
    file_access.resolve_academic_file_open_url = lambda **kwargs: None

    drive_root = ModuleType("ifitwala_drive")
    drive_services = ModuleType("ifitwala_drive.services")
    drive_files = ModuleType("ifitwala_drive.services.files")
    drive_derivatives = ModuleType("ifitwala_drive.services.files.derivatives")
    drive_derivatives.sync_preview_pipeline_for_current_version = lambda **kwargs: None
    pil_module = ModuleType("PIL")
    pil_image_module = ModuleType("PIL.Image")
    pil_module.Image = pil_image_module

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.api.file_access": file_access,
            "ifitwala_drive": drive_root,
            "ifitwala_drive.services": drive_services,
            "ifitwala_drive.services.files": drive_files,
            "ifitwala_drive.services.files.derivatives": drive_derivatives,
            "PIL": pil_module,
            "PIL.Image": pil_image_module,
        }
    ) as frappe:
        frappe.utils = SimpleNamespace(get_site_path=lambda *parts: "/tmp")
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.get_doc = lambda doctype, name: SimpleNamespace(name=name, doctype=doctype)
        yield import_fresh("ifitwala_ed.utilities.image_utils"), frappe


class TestImageUtilsUnit(TestCase):
    def test_get_preferred_employee_image_url_uses_ready_drive_derivative_role(self):
        with _image_utils_module() as (image_utils, frappe):
            image_utils.get_current_drive_files_for_slots = lambda **kwargs: [
                {
                    "name": "DRIVE-EMP-1",
                    "primary_subject_id": "EMP-0001",
                    "slot": "profile_image",
                    "file": "FILE-EMP-1",
                    "current_version": "DFV-EMP-1",
                }
            ]

            def fake_get_all(doctype, filters=None, fields=None, limit=None, order_by=None):
                del limit, order_by
                if doctype == "File":
                    return [
                        {
                            "name": "FILE-EMP-1",
                            "file_url": "/private/files/employee-source.png",
                            "is_private": 1,
                        }
                    ]
                if doctype == "Drive File Derivative":
                    self.assertEqual(filters["status"], "ready")
                    return [{"drive_file": "DRIVE-EMP-1", "derivative_role": "thumb"}]
                raise AssertionError(f"Unexpected get_all doctype: {doctype}")

            frappe.get_all = fake_get_all

            image_url = image_utils.get_preferred_employee_image_url(
                "EMP-0001",
                original_url="/private/files/employee-source.png",
            )

        self.assertIn("derivative_role=thumb", image_url)
        self.assertIn("file=FILE-EMP-1", image_url)

    def test_generate_employee_derivatives_schedules_drive_pipeline(self):
        file_doc = SimpleNamespace(
            name="FILE-EMP-1",
            attached_to_doctype="Employee",
            attached_to_field="employee_image",
            file_name="employee.png",
            file_url="/private/files/employee.png",
        )
        drive_file_row = {
            "name": "DRIVE-EMP-1",
            "slot": "profile_image",
            "current_version": "DFV-EMP-1",
        }
        drive_file_doc = SimpleNamespace(name="DRIVE-EMP-1", slot="profile_image", current_version="DFV-EMP-1")

        with _image_utils_module() as (image_utils, frappe):
            observed = []
            with (
                patch.object(image_utils, "_get_drive_file_row", return_value=drive_file_row),
                patch.object(frappe.db, "get_value", return_value="image/png"),
                patch.object(frappe, "get_doc", return_value=drive_file_doc),
                patch(
                    "ifitwala_drive.services.files.derivatives.sync_preview_pipeline_for_current_version",
                    side_effect=lambda **kwargs: observed.append(kwargs),
                ),
            ):
                image_utils._generate_employee_derivatives(file_doc)

        self.assertEqual(
            observed,
            [{"drive_file_doc": drive_file_doc, "mime_type": "image/png"}],
        )
