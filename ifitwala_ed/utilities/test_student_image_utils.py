# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import os
import shutil
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from PIL import Image

from ifitwala_ed.utilities import image_utils


class TestStudentImageUtils(FrappeTestCase):
    def tearDown(self):
        drive_root = frappe.utils.get_site_path("private", "files", "ifitwala_drive", "files", "bb")
        if os.path.isdir(drive_root):
            shutil.rmtree(drive_root, ignore_errors=True)

    def test_generate_student_derivatives_from_drive_private_file_url(self):
        relative_url = "/private/files/ifitwala_drive/files/bb/cc/student-source.png"
        absolute_path = frappe.utils.get_site_path(relative_url.lstrip("/"))
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        Image.new("RGB", (1200, 1200), color=(60, 90, 140)).save(absolute_path, "PNG")

        file_doc = frappe._dict(
            {
                "name": "FILE-STU-0001",
                "attached_to_doctype": "Student",
                "attached_to_name": "STU-0001",
                "attached_to_field": "student_image",
                "file_url": relative_url,
                "file_name": "student-source.png",
                "is_private": 0,
            }
        )
        drive_file = frappe._dict(
            {
                "owner_doctype": "Student",
                "owner_name": "STU-0001",
                "attached_doctype": "Student",
                "attached_name": "STU-0001",
                "primary_subject_type": "Student",
                "primary_subject_id": "STU-0001",
                "data_class": "identity_image",
                "purpose": "student_profile_display",
                "retention_policy": "until_school_exit_plus_6m",
                "slot": "profile_image",
                "organization": "ORG-0001",
                "school": "SCH-0001",
                "folder": None,
                "is_private": 0,
                "upload_source": "Desk",
            }
        )

        with (
            patch("ifitwala_ed.utilities.image_utils._get_drive_file_row", return_value=drive_file),
            patch("ifitwala_ed.utilities.image_utils._governed_derivative_exists", return_value=False),
            patch("ifitwala_ed.integrations.drive.content_uploads.upload_content_via_drive") as upload_content,
        ):
            image_utils._generate_student_derivatives(file_doc)

        self.assertEqual(upload_content.call_count, 3)
        created_slots = {call.kwargs["session_payload"]["slot"] for call in upload_content.call_args_list}
        self.assertEqual(
            created_slots,
            {"profile_image_thumb", "profile_image_card", "profile_image_medium"},
        )
        created_names = {call.kwargs["file_name"] for call in upload_content.call_args_list}
        self.assertEqual(
            created_names,
            {"thumb_student_source.webp", "card_student_source.webp", "medium_student_source.webp"},
        )

    def test_get_preferred_student_image_url_prefers_thumb_variant(self):
        classification_rows = [
            {
                "primary_subject_id": "STU-0001",
                "slot": "profile_image_medium",
                "file": "FILE-MEDIUM",
            },
            {
                "primary_subject_id": "STU-0001",
                "slot": "profile_image_thumb",
                "file": "FILE-THUMB",
            },
        ]
        file_rows = [
            {"name": "FILE-MEDIUM", "file_url": "/files/student/medium_student.webp", "is_private": 0},
            {"name": "FILE-THUMB", "file_url": "/files/student/thumb_student.webp", "is_private": 0},
        ]

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", return_value=True),
        ):
            image_url = image_utils.get_preferred_student_image_url(
                "STU-0001",
                original_url="/files/student/original_student.png",
            )

        self.assertEqual(image_url, "/files/student/thumb_student.webp")

    def test_apply_preferred_student_images_uses_academic_open_url_for_private_variant(self):
        thumb_url = "/private/files/ifitwala_drive/files/bb/cc/thumb_student.webp"
        rows = [{"name": "STU-0001", "student_image": None}]
        classification_rows = [
            {
                "primary_subject_id": "STU-0001",
                "slot": "profile_image_thumb",
                "file": "FILE-THUMB",
            },
        ]
        file_rows = [
            {"name": "FILE-THUMB", "file_url": thumb_url, "is_private": 1},
        ]

        def fake_get_value(doctype, filters, fieldname, as_dict=False):
            self.assertEqual(doctype, "Drive File")
            self.assertEqual(filters, {"file": "FILE-THUMB"})
            self.assertEqual(fieldname, ["storage_backend", "storage_object_key"])
            self.assertTrue(as_dict)
            return frappe._dict(
                {
                    "storage_backend": "gcs",
                    "storage_object_key": "files/bb/cc/thumb_student.webp",
                }
            )

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", return_value=False),
            patch("ifitwala_ed.utilities.image_utils.frappe.db.get_value", side_effect=fake_get_value),
        ):
            image_utils.apply_preferred_student_images(rows, student_field="name", image_field="student_image")

        self.assertEqual(
            rows[0]["student_image"],
            "/api/method/ifitwala_ed.api.file_access.download_academic_file"
            "?file=FILE-THUMB&context_doctype=Student&context_name=STU-0001",
        )
