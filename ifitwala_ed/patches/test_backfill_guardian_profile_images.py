from __future__ import annotations

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.backfill_guardian_profile_images import execute


class TestBackfillGuardianProfileImages(FrappeTestCase):
    def test_execute_repairs_existing_guardian_profile_images(self):
        guardian_rows = [
            {
                "name": "GRD-0001",
                "guardian_image": "/private/files/guardian-one.png",
                "organization": "ORG-0001",
            },
            {
                "name": "GRD-0002",
                "guardian_image": "/private/files/guardian-two.png",
                "organization": "",
            },
        ]

        with (
            patch("ifitwala_ed.patches.backfill_guardian_profile_images.frappe.db.table_exists", return_value=True),
            patch(
                "ifitwala_ed.patches.backfill_guardian_profile_images.frappe.get_all",
                return_value=guardian_rows,
            ) as mocked_get_all,
            patch("ifitwala_ed.patches.backfill_guardian_profile_images.ensure_guardian_profile_image") as ensure_image,
        ):
            execute()

        mocked_get_all.assert_called_once_with(
            "Guardian",
            filters={"guardian_image": ["is", "set"]},
            fields=["name", "guardian_image", "organization"],
            limit=100000,
        )
        ensure_image.assert_any_call(
            "GRD-0001",
            original_url="/private/files/guardian-one.png",
            organization="ORG-0001",
            upload_source="API",
        )
        ensure_image.assert_any_call(
            "GRD-0002",
            original_url="/private/files/guardian-two.png",
            organization="",
            upload_source="API",
        )
