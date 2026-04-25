from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.api.attachment_previews import build_attachment_preview_item


class TestAttachmentPreviewItems(TestCase):
    def test_build_attachment_preview_item_classifies_pdf_file_and_defaults_download_to_open(self):
        payload = build_attachment_preview_item(
            item_id="ATT-1",
            owner_doctype="Task Submission",
            owner_name="TSU-1",
            file_id="FILE-1",
            display_name="Essay Draft",
            extension="pdf",
            size_bytes="256",
            preview_status="ready",
            preview_url="/preview/file-1",
            open_url="/open/file-1",
        )

        self.assertEqual(payload["kind"], "pdf")
        self.assertEqual(payload["preview_mode"], "pdf_embed")
        self.assertEqual(payload["size_bytes"], 256)
        self.assertEqual(payload["download_url"], "/open/file-1")
        self.assertTrue(payload["can_preview"])
        self.assertTrue(payload["can_open"])
        self.assertTrue(payload["can_download"])

    def test_build_attachment_preview_item_classifies_external_link_without_download(self):
        payload = build_attachment_preview_item(
            item_id="ATT-2",
            owner_doctype="Org Communication",
            owner_name="COMM-1",
            link_url="https://example.com/reference",
            display_name="Reference",
            open_url="https://example.com/reference",
        )

        self.assertEqual(payload["kind"], "link")
        self.assertEqual(payload["preview_mode"], "external_link")
        self.assertFalse(payload["can_preview"])
        self.assertTrue(payload["can_open"])
        self.assertFalse(payload["can_download"])

    def test_build_attachment_preview_item_hides_internal_derivative_role_query_params(self):
        payload = build_attachment_preview_item(
            item_id="ATT-3",
            owner_doctype="Material Placement",
            owner_name="PLC-1",
            file_id="FILE-1",
            display_name="Lab PDF",
            extension="pdf",
            thumbnail_url=(
                "/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file"
                "?file=FILE-1&context_doctype=Material+Placement&derivative_role=pdf_card"
            ),
            preview_url=(
                "/api/method/ifitwala_ed.api.file_access.preview_academic_file"
                "?file=FILE-1&derivative_role=viewer_preview"
            ),
            open_url=(
                "/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1&derivative_role=thumb"
            ),
        )

        self.assertNotIn("derivative_role", payload["thumbnail_url"])
        self.assertIn("context_doctype=Material+Placement", payload["thumbnail_url"])
        self.assertNotIn("derivative_role", payload["preview_url"])
        self.assertNotIn("derivative_role", payload["open_url"])
        self.assertEqual(payload["download_url"], payload["open_url"])
