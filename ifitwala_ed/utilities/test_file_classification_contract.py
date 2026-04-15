from __future__ import annotations

import json
from pathlib import Path
from unittest import TestCase

from ifitwala_ed.utilities.file_classification_contract import ALLOWED_FILE_PURPOSES, LEARNING_RESOURCE_PURPOSE


def _load_select_options(doc_path: Path, fieldname: str) -> tuple[str, ...]:
    payload = json.loads(doc_path.read_text())
    field = next(row for row in payload.get("fields", []) if row.get("fieldname") == fieldname)
    return tuple(str(field.get("options") or "").splitlines())


class TestFileClassificationContract(TestCase):
    def test_learning_resource_is_part_of_the_canonical_purpose_catalog(self):
        self.assertIn(LEARNING_RESOURCE_PURPOSE, ALLOWED_FILE_PURPOSES)

    def test_file_classification_metadata_matches_the_canonical_purpose_catalog(self):
        repo_root = Path(__file__).resolve().parents[1]
        metadata_path = repo_root / "setup" / "doctype" / "file_classification" / "file_classification.json"
        self.assertEqual(_load_select_options(metadata_path, "purpose"), ALLOWED_FILE_PURPOSES)

    def test_applicant_document_type_metadata_reuses_the_canonical_purpose_catalog(self):
        repo_root = Path(__file__).resolve().parents[1]
        metadata_path = repo_root / "admission" / "doctype" / "applicant_document_type" / "applicant_document_type.json"
        self.assertEqual(_load_select_options(metadata_path, "classification_purpose"), ALLOWED_FILE_PURPOSES)
