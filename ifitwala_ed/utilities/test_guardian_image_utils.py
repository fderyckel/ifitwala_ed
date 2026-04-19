# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import os
import shutil
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from PIL import Image

from ifitwala_ed.utilities import image_utils


class TestGuardianImageUtils(FrappeTestCase):
    def tearDown(self):
        drive_root = frappe.utils.get_site_path("private", "files", "ifitwala_drive", "files", "aa")
        if os.path.isdir(drive_root):
            shutil.rmtree(drive_root, ignore_errors=True)

    def test_generate_guardian_derivatives_from_drive_private_file_url(self):
        relative_url = "/private/files/ifitwala_drive/files/aa/bb/guardian-source.png"
        absolute_path = frappe.utils.get_site_path(relative_url.lstrip("/"))
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        Image.new("RGB", (1200, 1200), color=(80, 40, 120)).save(absolute_path, "PNG")

        file_doc = frappe._dict(
            {
                "name": "FILE-GRD-0001",
                "attached_to_doctype": "Guardian",
                "attached_to_name": "GRD-0001",
                "attached_to_field": "guardian_image",
                "file_url": relative_url,
                "file_name": "guardian-source.png",
                "is_private": 0,
            }
        )
        drive_file = frappe._dict(
            {
                "owner_doctype": "Guardian",
                "owner_name": "GRD-0001",
                "attached_doctype": "Guardian",
                "attached_name": "GRD-0001",
                "primary_subject_type": "Guardian",
                "primary_subject_id": "GRD-0001",
                "data_class": "identity_image",
                "purpose": "guardian_profile_display",
                "retention_policy": "until_school_exit_plus_6m",
                "slot": "profile_image",
                "organization": "ORG-0001",
                "folder": None,
                "is_private": 0,
                "school": None,
                "upload_source": "Desk",
            }
        )

        with (
            patch("ifitwala_ed.utilities.image_utils._get_drive_file_row", return_value=drive_file),
            patch("ifitwala_ed.utilities.image_utils._governed_derivative_exists", return_value=False),
            patch("ifitwala_ed.integrations.drive.content_uploads.upload_content_via_drive") as upload_content,
        ):
            image_utils._generate_guardian_derivatives(file_doc)

        self.assertEqual(upload_content.call_count, 3)
        created_slots = {call.kwargs["session_payload"]["slot"] for call in upload_content.call_args_list}
        self.assertEqual(
            created_slots,
            {"profile_image_thumb", "profile_image_card", "profile_image_medium"},
        )

    def test_get_preferred_guardian_image_url_prefers_thumb_variant(self):
        classification_rows = [
            {
                "primary_subject_id": "GRD-0001",
                "slot": "profile_image_medium",
                "file": "FILE-MEDIUM",
            },
            {
                "primary_subject_id": "GRD-0001",
                "slot": "profile_image_thumb",
                "file": "FILE-THUMB",
            },
        ]
        file_rows = [
            {"name": "FILE-MEDIUM", "file_url": "/files/guardian/medium_guardian.webp", "is_private": 0},
            {"name": "FILE-THUMB", "file_url": "/files/guardian/thumb_guardian.webp", "is_private": 0},
        ]

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", return_value=True),
        ):
            image_url = image_utils.get_preferred_guardian_image_url(
                "GRD-0001",
                original_url="/files/guardian/original_guardian.png",
            )

        self.assertEqual(image_url, "/files/guardian/thumb_guardian.webp")

    def test_apply_preferred_guardian_images_uses_guardian_open_url_for_private_variant(self):
        thumb_url = "/private/files/ifitwala_drive/files/aa/bb/thumb_guardian.webp"
        rows = [{"name": "GRD-0001", "guardian_image": None}]
        classification_rows = [
            {
                "primary_subject_id": "GRD-0001",
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
                    "storage_object_key": "files/aa/bb/thumb_guardian.webp",
                }
            )

        with (
            patch("ifitwala_ed.utilities.image_utils.frappe.get_all", side_effect=[classification_rows, file_rows]),
            patch("ifitwala_ed.utilities.image_utils.file_url_exists_on_disk", return_value=False),
            patch("ifitwala_ed.utilities.image_utils.frappe.db.get_value", side_effect=fake_get_value),
        ):
            image_utils.apply_preferred_guardian_images(rows, guardian_field="name", image_field="guardian_image")

        self.assertEqual(
            rows[0]["guardian_image"],
            "/api/method/ifitwala_ed.api.file_access.download_guardian_file"
            "?file=FILE-THUMB&context_doctype=Guardian&context_name=GRD-0001",
        )

    def test_ensure_guardian_profile_image_reuses_current_governed_source_and_syncs_field(self):
        guardian_doc = frappe._dict({"name": "GRD-0001", "organization": "ORG-0001"})
        current_file_doc = frappe._dict(
            {
                "name": "FILE-GRD-CURRENT",
                "file_url": "/private/files/guardian-current.png",
            }
        )
        drive_file = {
            "organization": "ORG-0001",
        }
        contract = {
            "primary_subject_type": "Guardian",
            "primary_subject_id": "GRD-0001",
            "data_class": "identity_image",
            "purpose": "guardian_profile_display",
            "retention_policy": "until_school_exit_plus_6m",
            "slot": "profile_image",
            "organization": "ORG-0001",
            "school": None,
        }

        with (
            patch(
                "ifitwala_ed.utilities.image_utils._get_current_governed_profile_file", return_value=current_file_doc
            ),
            patch("ifitwala_ed.utilities.image_utils._get_drive_file_row", return_value=drive_file),
            patch("ifitwala_ed.utilities.image_utils.frappe.get_doc", return_value=guardian_doc),
            patch("ifitwala_ed.integrations.drive.media.build_guardian_image_contract", return_value=contract),
            patch("ifitwala_ed.utilities.image_utils._generate_guardian_derivatives") as generate_derivatives,
            patch("ifitwala_ed.utilities.image_utils.frappe.db.set_value") as set_value,
        ):
            image_url = image_utils.ensure_guardian_profile_image("GRD-0001")

        self.assertEqual(image_url, "/private/files/guardian-current.png")
        generate_derivatives.assert_called_once_with(current_file_doc)
        set_value.assert_called_once_with(
            "Guardian",
            "GRD-0001",
            {
                "guardian_image": "/private/files/guardian-current.png",
                "organization": "ORG-0001",
            },
            update_modified=False,
        )

    def test_ensure_guardian_profile_image_uploads_drive_managed_copy_when_source_exists(self):
        guardian_doc = frappe._dict({"name": "GRD-0001", "organization": "ORG-0001"})
        source_file_doc = frappe._dict(
            {
                "name": "FILE-GRD-0001",
                "attached_to_doctype": "Guardian",
                "attached_to_name": "GRD-0001",
                "attached_to_field": "guardian_image",
                "file_url": "/private/files/guardian-source.png",
                "file_name": "guardian-source.png",
            }
        )
        contract = {
            "primary_subject_type": "Guardian",
            "primary_subject_id": "GRD-0001",
            "data_class": "identity_image",
            "purpose": "guardian_profile_display",
            "retention_policy": "until_school_exit_plus_6m",
            "slot": "profile_image",
            "organization": "ORG-0001",
            "school": None,
        }
        uploaded_file_doc = frappe._dict(
            {
                "name": "FILE-GRD-UPLOADED",
                "file_url": "/private/files/guardian-source.png",
            }
        )

        with (
            patch("ifitwala_ed.utilities.image_utils._get_current_governed_profile_file", return_value=None),
            patch("ifitwala_ed.utilities.image_utils.frappe.get_doc", return_value=guardian_doc),
            patch("ifitwala_ed.integrations.drive.media.build_guardian_image_contract", return_value=contract),
            patch("ifitwala_ed.utilities.image_utils._resolve_unique_file_doc_by_url", return_value=source_file_doc),
            patch("ifitwala_ed.utilities.image_utils._read_managed_file_bytes", return_value=b"guardian-bytes"),
            patch(
                "ifitwala_ed.integrations.drive.content_uploads.upload_content_via_drive",
                return_value=({}, {}, uploaded_file_doc),
            ) as upload_content,
            patch("ifitwala_ed.utilities.image_utils._load_drive_module") as load_drive_module,
            patch("ifitwala_ed.utilities.image_utils.frappe.db.set_value") as set_value,
        ):
            load_drive_module.return_value = frappe._dict({"upload_guardian_image": object()})
            image_url = image_utils.ensure_guardian_profile_image(
                "GRD-0001",
                original_url="/private/files/guardian-source.png",
            )

        self.assertEqual(image_url, "/private/files/guardian-source.png")
        upload_content.assert_called_once()
        set_value.assert_called_once_with(
            "Guardian",
            "GRD-0001",
            {
                "guardian_image": "/private/files/guardian-source.png",
                "organization": "ORG-0001",
            },
            update_modified=False,
        )
