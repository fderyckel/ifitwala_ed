# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import os
import shutil
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from PIL import Image

from ifitwala_ed.utilities import image_utils


class TestEmployeeImageUtils(FrappeTestCase):
    def tearDown(self):
        drive_root = frappe.utils.get_site_path("private", "files", "ifitwala_drive", "files", "aa")
        if os.path.isdir(drive_root):
            shutil.rmtree(drive_root, ignore_errors=True)

    def test_generate_employee_derivatives_from_drive_private_file_url(self):
        relative_url = "/private/files/ifitwala_drive/files/aa/bb/employee-source.png"
        absolute_path = frappe.utils.get_site_path(relative_url.lstrip("/"))
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        Image.new("RGB", (1200, 1200), color=(40, 80, 120)).save(absolute_path, "PNG")

        file_doc = frappe._dict(
            {
                "name": "FILE-EMP-0001",
                "attached_to_doctype": "Employee",
                "attached_to_name": "EMP-0001",
                "attached_to_field": "employee_image",
                "file_url": relative_url,
                "file_name": "employee-source.png",
                "is_private": 0,
            }
        )
        classification = frappe._dict(
            {
                "primary_subject_type": "Employee",
                "primary_subject_id": "EMP-0001",
                "data_class": "identity_image",
                "purpose": "employee_profile_display",
                "retention_policy": "employment_duration_plus_grace",
                "slot": "profile_image",
                "organization": "ORG-0001",
                "school": "SCH-0001",
                "upload_source": "Desk",
                "secondary_subjects": [],
            }
        )

        with (
            patch("ifitwala_ed.utilities.image_utils._get_file_classification", return_value=classification),
            patch("ifitwala_ed.utilities.image_utils._employee_derivative_exists", return_value=False),
            patch("ifitwala_ed.utilities.file_dispatcher.create_and_classify_file") as create_and_classify,
        ):
            image_utils._generate_employee_derivatives(file_doc)

        self.assertEqual(create_and_classify.call_count, 3)
        created_slots = {call.kwargs["classification"]["slot"] for call in create_and_classify.call_args_list}
        self.assertEqual(
            created_slots,
            {"profile_image_thumb", "profile_image_card", "profile_image_medium"},
        )
        created_names = {call.kwargs["file_kwargs"]["file_name"] for call in create_and_classify.call_args_list}
        self.assertEqual(
            created_names,
            {"thumb_employee_source.webp", "card_employee_source.webp", "medium_employee_source.webp"},
        )

    def test_get_preferred_employee_image_url_prefers_thumb_variant(self):
        classification_rows = [
            {
                "primary_subject_id": "EMP-0001",
                "slot": "profile_image_medium",
                "file": "FILE-MEDIUM",
            },
            {
                "primary_subject_id": "EMP-0001",
                "slot": "profile_image_thumb",
                "file": "FILE-THUMB",
            },
        ]
        file_rows = [
            {"name": "FILE-MEDIUM", "file_url": "/files/employee/medium_employee.webp", "is_private": 0},
            {"name": "FILE-THUMB", "file_url": "/files/employee/thumb_employee.webp", "is_private": 0},
        ]

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", return_value=True),
        ):
            image_url = image_utils.get_preferred_employee_image_url(
                "EMP-0001",
                original_url="/files/employee/original_employee.png",
            )

        self.assertEqual(image_url, "/files/employee/thumb_employee.webp")

    def test_get_preferred_employee_image_url_accepts_drive_backed_thumb_variant(self):
        thumb_url = "/private/files/ifitwala_drive/files/aa/bb/thumb_employee.webp"
        classification_rows = [
            {
                "primary_subject_id": "EMP-0001",
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
                    "storage_object_key": "files/aa/bb/thumb_employee.webp",
                }
            )

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", return_value=False),
            patch("ifitwala_ed.utilities.image_utils.frappe.db.get_value", side_effect=fake_get_value),
            patch(
                "ifitwala_ed.api.file_access.resolve_employee_file_open_url",
                return_value="/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-THUMB&context_doctype=Employee&context_name=EMP-0001",
            ) as resolve_open_url,
        ):
            image_url = image_utils.get_preferred_employee_image_url(
                "EMP-0001",
                original_url="/files/employee/original_employee.png",
            )

        resolve_open_url.assert_called_once_with(
            file_name="FILE-THUMB",
            file_url=thumb_url,
            context_doctype="Employee",
            context_name="EMP-0001",
        )
        self.assertEqual(
            image_url,
            "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-THUMB&context_doctype=Employee&context_name=EMP-0001",
        )

    def test_apply_preferred_employee_images_keeps_employee_specific_variants(self):
        classification_rows = [
            {
                "primary_subject_id": "EMP-0001",
                "slot": "profile_image_card",
                "file": "FILE-CARD-1",
            },
            {
                "primary_subject_id": "EMP-0002",
                "slot": "profile_image_thumb",
                "file": "FILE-THUMB-2",
            },
        ]
        file_rows = [
            {"name": "FILE-CARD-1", "file_url": "/files/employee/card_employee_1.webp", "is_private": 0},
            {"name": "FILE-THUMB-2", "file_url": "/files/employee/thumb_employee_2.webp", "is_private": 0},
        ]
        rows = [
            {"id": "EMP-0001", "image": "/files/employee/original_employee_1.png"},
            {"id": "EMP-0002", "image": "/files/employee/original_employee_2.png"},
            {"id": "EMP-0003", "image": "/files/employee/original_employee_3.png"},
        ]

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", return_value=True),
        ):
            resolved = image_utils.apply_preferred_employee_images(rows)

        self.assertEqual(resolved[0]["image"], "/files/employee/card_employee_1.webp")
        self.assertEqual(resolved[1]["image"], "/files/employee/thumb_employee_2.webp")
        self.assertEqual(resolved[2]["image"], "/files/employee/original_employee_3.png")

    def test_apply_preferred_employee_images_falls_back_to_original_when_variant_is_missing(self):
        classification_rows = [
            {
                "primary_subject_id": "EMP-0001",
                "slot": "profile_image_thumb",
                "file": "FILE-BROKEN-THUMB",
            },
        ]
        file_rows = [
            {"name": "FILE-BROKEN-THUMB", "file_url": "/files/employee/thumb_broken.webp", "is_private": 0},
        ]
        rows = [
            {"id": "EMP-0001", "image": "/files/employee/original_employee.png"},
        ]

        def fake_file_exists(file_url, is_private=0):
            return file_url != "/files/employee/thumb_broken.webp"

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", side_effect=fake_file_exists),
        ):
            resolved = image_utils.apply_preferred_employee_images(rows)

        self.assertEqual(resolved[0]["image"], "/files/employee/original_employee.png")

    def test_apply_preferred_employee_images_can_skip_original_fallback(self):
        classification_rows = [
            {
                "primary_subject_id": "EMP-0001",
                "slot": "profile_image_thumb",
                "file": "FILE-BROKEN-THUMB",
            },
        ]
        file_rows = [
            {"name": "FILE-BROKEN-THUMB", "file_url": "/files/employee/thumb_broken.webp", "is_private": 0},
        ]
        rows = [
            {"id": "EMP-0001", "image": "/files/employee/original_employee.png"},
        ]

        def fake_file_exists(file_url, is_private=0):
            return file_url != "/files/employee/thumb_broken.webp"

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", side_effect=fake_file_exists),
        ):
            resolved = image_utils.apply_preferred_employee_images(
                rows,
                slots=("profile_image_thumb", "profile_image_card", "profile_image_medium"),
                fallback_to_original=False,
            )

        self.assertIsNone(resolved[0]["image"])
