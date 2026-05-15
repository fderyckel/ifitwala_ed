from __future__ import annotations

import json
from pathlib import Path
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

    def test_build_attachment_preview_item_hides_raw_private_signed_and_storage_urls(self):
        payload = build_attachment_preview_item(
            item_id="ATT-4",
            owner_doctype="Task Submission",
            owner_name="TSU-1",
            file_id="FILE-1",
            display_name="Unsafe",
            thumbnail_url="/private/files/thumb.webp",
            preview_url="https://storage.example.com/object?X-Amz-Signature=abc",
            open_url="files/aa/bb/object.pdf",
            download_url="derivatives/aa/bb/object.webp",
        )
        serialized = json.dumps(payload, sort_keys=True)

        self.assertIsNone(payload["thumbnail_url"])
        self.assertIsNone(payload["preview_url"])
        self.assertIsNone(payload["open_url"])
        self.assertIsNone(payload["download_url"])
        self.assertFalse(payload["can_preview"])
        self.assertFalse(payload["can_open"])
        self.assertFalse(payload["can_download"])
        self.assertNotIn("/private/", serialized)
        self.assertNotIn("X-Amz-Signature", serialized)
        self.assertNotIn("files/aa/bb", serialized)
        self.assertNotIn("derivatives/aa/bb", serialized)

    def test_build_attachment_preview_item_degrades_non_ready_previews_to_open_only(self):
        for status in ("pending", "processing", "failed", "unsupported", "not_applicable"):
            with self.subTest(status=status):
                payload = build_attachment_preview_item(
                    item_id="ATT-5",
                    owner_doctype="Student Log",
                    owner_name="SLOG-1",
                    file_id="FILE-1",
                    display_name="Evidence PDF",
                    extension="pdf",
                    preview_status=status,
                    thumbnail_url="/thumb/file-1",
                    preview_url="/preview/file-1",
                    open_url="/open/file-1",
                )

                self.assertEqual(payload["preview_status"], status)
                self.assertIsNone(payload["thumbnail_url"])
                self.assertIsNone(payload["preview_url"])
                self.assertEqual(payload["open_url"], "/open/file-1")
                self.assertEqual(payload["download_url"], "/open/file-1")
                self.assertEqual(payload["preview_mode"], "icon_only")
                self.assertFalse(payload["can_preview"])
                self.assertTrue(payload["can_open"])
                self.assertTrue(payload["can_download"])

    def test_public_preview_docs_and_spa_contracts_do_not_expose_derivative_roles(self):
        repo_root = Path(__file__).resolve().parents[2]
        docs_roots = (
            repo_root / "ifitwala_ed" / "docs" / "files_and_policies",
            repo_root / "ifitwala_ed" / "docs" / "admission",
            repo_root / "ifitwala_ed" / "docs" / "hr",
            repo_root / "ifitwala_ed" / "docs" / "website",
        )
        spa_root = repo_root / "ifitwala_ed" / "ui-spa" / "src"
        forbidden_doc_snippets = ("`thumb`", "`card`", "`viewer_preview`", "`pdf_card`")
        forbidden_public_contract_snippets = (
            "derivative_role",
            "derivative_roles",
            "viewer_preview",
            "pdf_card",
        )
        failures: list[str] = []

        for root in docs_roots:
            for path in root.rglob("*.md"):
                text = path.read_text()
                for snippet in forbidden_doc_snippets:
                    if snippet in text:
                        failures.append(f"{path.relative_to(repo_root)} contains {snippet}")

        for suffix in ("*.ts", "*.vue"):
            for path in spa_root.rglob(suffix):
                text = path.read_text()
                for snippet in forbidden_public_contract_snippets:
                    if snippet in text:
                        failures.append(f"{path.relative_to(repo_root)} contains {snippet}")

        self.assertEqual([], failures)
