from __future__ import annotations

import json
import re
from pathlib import Path
from unittest import TestCase

from ifitwala_ed.utilities.governed_file_contract import ALLOWED_FILE_PURPOSES, LEARNING_RESOURCE_PURPOSE


def _load_select_options(doc_path: Path, fieldname: str) -> tuple[str, ...]:
    payload = json.loads(doc_path.read_text())
    field = next(row for row in payload.get("fields", []) if row.get("fieldname") == fieldname)
    return tuple(str(field.get("options") or "").splitlines())


class TestGovernedFileContract(TestCase):
    def test_learning_resource_is_part_of_the_canonical_purpose_catalog(self):
        self.assertIn(LEARNING_RESOURCE_PURPOSE, ALLOWED_FILE_PURPOSES)

    def test_legacy_file_classification_metadata_is_removed_from_repo(self):
        repo_root = Path(__file__).resolve().parents[1]
        metadata_path = repo_root / "setup" / "doctype" / "file_classification" / "file_classification.json"
        self.assertFalse(metadata_path.exists())

    def test_applicant_document_type_metadata_reuses_the_canonical_purpose_catalog(self):
        repo_root = Path(__file__).resolve().parents[1]
        metadata_path = repo_root / "admission" / "doctype" / "applicant_document_type" / "applicant_document_type.json"
        self.assertEqual(_load_select_options(metadata_path, "classification_purpose"), ALLOWED_FILE_PURPOSES)

    def test_canonical_file_semantics_docs_use_only_allowed_purposes(self):
        repo_root = Path(__file__).resolve().parents[1]
        docs_path = (
            repo_root / "docs" / "files_and_policies" / "files_07_education_file_semantics_and_cross_app_contract.md"
        )
        text = docs_path.read_text()
        allowed = set(ALLOWED_FILE_PURPOSES)

        discovered: list[str] = []

        purpose_catalog = text.split("## 3. Canonical purpose direction", 1)[1].split(
            "## 4. Canonical workflow contract", 1
        )[0]
        for line in purpose_catalog.splitlines():
            if not line.startswith("| `"):
                continue
            match = re.search(r"\|\s*`([^`]+)`", line)
            if match:
                discovered.append(match.group(1))

        surface_mapping = text.split("## 8. Surface mapping", 1)[1].split("## 9. End-state rule", 1)[0]
        for line in surface_mapping.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 2 or not cells[1].startswith("`"):
                continue
            match = re.fullmatch(r"`([^`]+)`", cells[1])
            if match:
                discovered.append(match.group(1))

        unknown = sorted({purpose for purpose in discovered if purpose not in allowed})
        self.assertEqual(unknown, [])

    def test_expense_reimbursement_doc_uses_allowed_receipt_purpose(self):
        repo_root = Path(__file__).resolve().parents[1]
        docs_path = repo_root / "docs" / "hr" / "expense_reimbursement.md"
        text = docs_path.read_text()
        match = re.search(r"- purpose: `([^`]+)`", text)
        self.assertIsNotNone(match)
        self.assertIn(match.group(1), ALLOWED_FILE_PURPOSES)
