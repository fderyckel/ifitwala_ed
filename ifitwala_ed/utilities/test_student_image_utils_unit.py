from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _student_image_utils_module():
    file_access = ModuleType("ifitwala_ed.api.file_access")
    file_access.resolve_employee_file_open_url = lambda **kwargs: None
    file_access.resolve_guardian_file_open_url = lambda **kwargs: None
    file_access.resolve_academic_file_open_url = lambda **kwargs: None

    authority = ModuleType("ifitwala_ed.integrations.drive.authority")
    authority.get_current_drive_file_for_slot = lambda **kwargs: None
    authority.get_current_drive_files_for_slots = lambda **kwargs: []
    authority.get_drive_file_for_file = lambda *args, **kwargs: None
    authority.is_governed_file = lambda *args, **kwargs: False

    media_client = ModuleType("ifitwala_ed.integrations.drive.media_client")
    media_client.request_profile_image_preview_derivatives = lambda *args, **kwargs: None

    drive_api = ModuleType("ifitwala_drive.api")
    drive_media_api = ModuleType("ifitwala_drive.api.media")
    drive_media_api.upload_student_image = object()

    drive_media = ModuleType("ifitwala_ed.integrations.drive.media")
    drive_media.build_student_image_contract = lambda student_doc: {}

    drive_content_uploads = ModuleType("ifitwala_ed.integrations.drive.content_uploads")
    drive_content_uploads.upload_content_via_drive = lambda **kwargs: ({}, {}, None)

    drive_root = ModuleType("ifitwala_drive")
    pil_module = ModuleType("PIL")
    pil_image_module = ModuleType("PIL.Image")
    pil_module.Image = pil_image_module

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.api.file_access": file_access,
            "ifitwala_ed.integrations.drive.authority": authority,
            "ifitwala_ed.integrations.drive.media_client": media_client,
            "ifitwala_drive.api": drive_api,
            "ifitwala_drive.api.media": drive_media_api,
            "ifitwala_ed.integrations.drive.media": drive_media,
            "ifitwala_ed.integrations.drive.content_uploads": drive_content_uploads,
            "ifitwala_drive": drive_root,
            "PIL": pil_module,
            "PIL.Image": pil_image_module,
        }
    ) as frappe:
        frappe.utils = SimpleNamespace(get_site_path=lambda *parts: "/tmp")
        frappe.db.exists = lambda *args, **kwargs: False
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.set_value = lambda *args, **kwargs: None
        frappe.get_all = lambda *args, **kwargs: []
        frappe.get_doc = lambda doctype, name: SimpleNamespace(name=name, doctype=doctype)
        yield import_fresh("ifitwala_ed.utilities.image_utils"), frappe


class TestStudentImageUtilsUnit(TestCase):
    def test_ensure_student_profile_image_reuses_current_governed_source_and_syncs_field(self):
        with _student_image_utils_module() as (image_utils, frappe):
            current_file_doc = SimpleNamespace(
                name="FILE-STU-CURRENT",
                file_url="/private/files/student-current.png",
            )
            set_calls = []
            frappe.db.set_value = lambda *args, **kwargs: set_calls.append((args, kwargs))

            with patch.object(
                image_utils,
                "_get_current_governed_profile_file",
                return_value=current_file_doc,
            ):
                image_url = image_utils.ensure_student_profile_image("STU-0001")

        self.assertEqual(image_url, "/private/files/student-current.png")
        self.assertEqual(
            set_calls,
            [
                (
                    ("Student", "STU-0001", "student_image", "/private/files/student-current.png"),
                    {"update_modified": False},
                )
            ],
        )

    def test_ensure_student_profile_image_uploads_drive_managed_copy_when_source_exists(self):
        with _student_image_utils_module() as (image_utils, frappe):
            student_doc = SimpleNamespace(
                name="STU-0001",
                anchor_school="SCH-0001",
                student_image="/private/files/student-source.png",
            )
            source_file_doc = SimpleNamespace(
                name="FILE-STU-0001",
                attached_to_doctype="Student",
                attached_to_name="STU-0001",
                attached_to_field="student_image",
                file_url="/private/files/student-source.png",
                file_name="student-source.png",
            )
            uploaded_file_doc = SimpleNamespace(
                name="FILE-STU-UPLOADED",
                file_url="/private/files/student-source.png",
            )
            set_calls = []
            frappe.get_doc = lambda doctype, name: student_doc if doctype == "Student" else source_file_doc
            frappe.db.set_value = lambda *args, **kwargs: set_calls.append((args, kwargs))

            with (
                patch.object(image_utils, "_get_current_governed_profile_file", return_value=None),
                patch.object(image_utils, "_resolve_unique_file_doc_by_url", return_value=source_file_doc),
                patch.object(image_utils, "_read_managed_file_bytes", return_value=b"student-bytes"),
                patch(
                    "ifitwala_ed.integrations.drive.content_uploads.upload_content_via_drive",
                    return_value=({}, {}, uploaded_file_doc),
                ) as upload_content,
            ):
                image_url = image_utils.ensure_student_profile_image(
                    "STU-0001",
                    original_url="/private/files/student-source.png",
                )

        self.assertEqual(image_url, "/private/files/student-source.png")
        upload_content.assert_called_once()
        self.assertEqual(
            set_calls,
            [
                (
                    ("Student", "STU-0001", "student_image", "/private/files/student-source.png"),
                    {"update_modified": False},
                )
            ],
        )
