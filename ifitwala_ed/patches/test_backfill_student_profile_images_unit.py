from __future__ import annotations

from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillStudentProfileImagesUnit(TestCase):
    def test_execute_repairs_existing_student_profile_images(self):
        student_rows = [
            {
                "name": "STU-0001",
                "student_image": "/private/files/student-one.png",
            },
            {
                "name": "STU-0002",
                "student_image": "/private/files/student-two.png",
            },
        ]

        authority = ModuleType("ifitwala_ed.integrations.drive.authority")
        authority.get_current_drive_file_for_slot = lambda **kwargs: None
        authority.get_current_drive_files_for_slots = lambda **kwargs: []
        authority.get_drive_file_for_file = lambda *args, **kwargs: None
        authority.is_governed_file = lambda *args, **kwargs: False
        media_client = ModuleType("ifitwala_ed.integrations.drive.media_client")
        media_client.request_profile_image_preview_derivatives = lambda *args, **kwargs: None
        pil_module = ModuleType("PIL")
        pil_image_module = ModuleType("PIL.Image")
        pil_module.Image = pil_image_module

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.integrations.drive.authority": authority,
                "ifitwala_ed.integrations.drive.media_client": media_client,
                "PIL": pil_module,
                "PIL.Image": pil_image_module,
            }
        ) as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Student", "File"}
            module = import_fresh("ifitwala_ed.patches.backfill_student_profile_images")

            with (
                patch.object(module.frappe, "get_all", return_value=student_rows) as mocked_get_all,
                patch.object(module, "ensure_student_profile_image") as ensure_image,
            ):
                module.execute()

        mocked_get_all.assert_called_once_with(
            "Student",
            filters={"student_image": ["is", "set"]},
            fields=["name", "student_image"],
            limit=100000,
        )
        ensure_image.assert_any_call(
            "STU-0001",
            original_url="/private/files/student-one.png",
            upload_source="API",
        )
        ensure_image.assert_any_call(
            "STU-0002",
            original_url="/private/files/student-two.png",
            upload_source="API",
        )
