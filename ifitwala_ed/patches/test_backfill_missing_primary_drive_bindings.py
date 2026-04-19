from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _patch_module():
    docs = {
        ("Drive Upload Session", "DUS-0001"): SimpleNamespace(name="DUS-0001"),
    }

    with stubbed_frappe() as frappe:
        frappe.db = SimpleNamespace()
        frappe.db.table_exists = lambda doctype: True
        frappe.get_doc = lambda doctype, name: docs[(doctype, name)]
        frappe.get_traceback = lambda: "traceback"
        yield import_fresh("ifitwala_ed.patches.backfill_missing_primary_drive_bindings"), frappe


class TestBackfillMissingPrimaryDriveBindings(TestCase):
    def test_execute_creates_missing_primary_binding_when_contract_requires_one(self):
        with _patch_module() as (module, frappe):
            module._load_candidate_drive_files = lambda: [
                {
                    "name": "DF-0001",
                    "file": "FILE-0001",
                    "source_upload_session": "DUS-0001",
                    "status": "active",
                }
            ]
            module._resolve_binding_role = lambda upload_session_doc: "general_reference"
            observed = {}
            module._create_primary_binding = lambda **kwargs: observed.update(kwargs) or "DB-0001"
            frappe.db.get_value = lambda doctype, filters=None, fieldname=None, as_dict=False: None

            module.execute()

            self.assertEqual(observed["drive_file_id"], "DF-0001")
            self.assertEqual(observed["file_id"], "FILE-0001")
            self.assertEqual(observed["binding_role"], "general_reference")
            self.assertEqual(observed["upload_session_doc"].name, "DUS-0001")

    def test_execute_skips_rows_that_already_have_active_primary_binding(self):
        with _patch_module() as (module, frappe):
            module._load_candidate_drive_files = lambda: [
                {
                    "name": "DF-0002",
                    "file": "FILE-0002",
                    "source_upload_session": "DUS-0001",
                    "status": "active",
                }
            ]
            module._resolve_binding_role = lambda upload_session_doc: "general_reference"
            created = []
            module._create_primary_binding = lambda **kwargs: created.append(kwargs) or "DB-0002"

            def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
                if doctype == "Drive Binding":
                    return "DB-EXISTING"
                return None

            frappe.db.get_value = fake_get_value

            module.execute()

            self.assertEqual(created, [])
