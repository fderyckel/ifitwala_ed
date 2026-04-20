# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.utilities import image_utils


class TestGuardianImageUtils(FrappeTestCase):
    def test_get_preferred_guardian_image_url_prefers_thumb_variant(self):
        with patch(
            "ifitwala_ed.utilities.image_utils._get_governed_image_variants_map",
            return_value={
                "GRD-0001": {
                    "profile_image_thumb": "/api/method/ifitwala_ed.api.file_access.download_guardian_file?file=FILE-THUMB&context_doctype=Guardian&context_name=GRD-0001&derivative_role=thumb",
                    "profile_image_card": "/api/method/ifitwala_ed.api.file_access.download_guardian_file?file=FILE-CARD&context_doctype=Guardian&context_name=GRD-0001&derivative_role=card",
                }
            },
        ):
            image_url = image_utils.get_preferred_guardian_image_url(
                "GRD-0001",
                original_url="/private/files/guardian/original_guardian.png",
            )

        self.assertEqual(
            image_url,
            "/api/method/ifitwala_ed.api.file_access.download_guardian_file?file=FILE-THUMB&context_doctype=Guardian&context_name=GRD-0001&derivative_role=thumb",
        )

    def test_apply_preferred_guardian_images_uses_governed_variant_routes(self):
        rows = [{"name": "GRD-0001", "guardian_image": "/private/files/guardian/original_guardian.png"}]

        with patch(
            "ifitwala_ed.utilities.image_utils._get_governed_image_variants_map",
            return_value={
                "GRD-0001": {
                    "profile_image_thumb": "/api/method/ifitwala_ed.api.file_access.download_guardian_file?file=FILE-THUMB&context_doctype=Guardian&context_name=GRD-0001&derivative_role=thumb"
                }
            },
        ):
            image_utils.apply_preferred_guardian_images(rows, guardian_field="name", image_field="guardian_image")

        self.assertEqual(
            rows[0]["guardian_image"],
            "/api/method/ifitwala_ed.api.file_access.download_guardian_file?file=FILE-THUMB&context_doctype=Guardian&context_name=GRD-0001&derivative_role=thumb",
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

        with (
            patch(
                "ifitwala_ed.utilities.image_utils._get_current_governed_profile_file", return_value=current_file_doc
            ),
            patch("ifitwala_ed.utilities.image_utils._get_drive_file_row", return_value=drive_file),
            patch("ifitwala_ed.utilities.image_utils.frappe.get_doc", return_value=guardian_doc),
            patch("ifitwala_ed.utilities.image_utils.frappe.db.set_value") as set_value,
        ):
            image_url = image_utils.ensure_guardian_profile_image("GRD-0001")

        self.assertEqual(image_url, "/private/files/guardian-current.png")
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
