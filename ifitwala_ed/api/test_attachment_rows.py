from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.api.attachment_rows import build_governed_attachment_row


class TestGovernedAttachmentRows(TestCase):
    def test_build_governed_attachment_row_adds_surface_identity_without_weakening_preview_rules(self):
        row = build_governed_attachment_row(
            row_id="DRV-1",
            surface="admissions.applicant_document",
            item_id="DRV-1",
            owner_doctype="Student Applicant",
            owner_name="APPL-0001",
            file_id="DRV-1",
            display_name="passport.pdf",
            extension="pdf",
            preview_status="processing",
            thumbnail_url="/api/method/ifitwala_ed.api.file_access.thumbnail_admissions_file?drive_file_id=DRV-1",
            preview_url="/api/method/ifitwala_ed.api.file_access.preview_admissions_file?drive_file_id=DRV-1",
            open_url="/api/method/ifitwala_ed.api.file_access.download_admissions_file?drive_file_id=DRV-1",
        )

        self.assertEqual(row["id"], "DRV-1")
        self.assertEqual(row["surface"], "admissions.applicant_document")
        self.assertEqual(row["item_id"], "DRV-1")
        self.assertIsNone(row["thumbnail_url"])
        self.assertIsNone(row["preview_url"])
        self.assertTrue(row["open_url"])
        self.assertTrue(row["can_open"])
        self.assertFalse(row["can_preview"])
