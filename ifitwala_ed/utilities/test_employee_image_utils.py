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
