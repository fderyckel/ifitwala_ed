from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _patch_module():
    docs = {
        (
            "Drive Upload Session",
            "DUS-0001",
        ): SimpleNamespace(
            name="DUS-0001",
            attached_doctype="Supporting Material",
            attached_name="MAT-0001",
            owner_doctype="Supporting Material",
            owner_name="MAT-0001",
            intended_slot="resource",
        ),
    }

    with stubbed_frappe() as frappe:
        frappe.db = SimpleNamespace()
        frappe.db.table_exists = lambda doctype: True
        frappe.db.exists = lambda doctype, name: True
        frappe.get_doc = lambda doctype, name: docs[(doctype, name)]
        frappe.get_traceback = lambda: "traceback"
        frappe.as_json = lambda payload, indent=None: str(payload)
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

    def test_execute_falls_back_to_legacy_binding_role_inference(self):
        with _patch_module() as (module, frappe):
            module._load_candidate_drive_files = lambda: [
                {
                    "name": "DF-0003",
                    "file": "FILE-0003",
                    "source_upload_session": "DUS-0001",
                    "status": "active",
                    "attached_doctype": "Supporting Material",
                    "attached_name": "MAT-0001",
                    "owner_doctype": "Supporting Material",
                    "owner_name": "MAT-0001",
                    "slot": "resource",
                }
            ]
            observed = {}
            module._resolve_binding_role = lambda upload_session_doc: (_ for _ in ()).throw(Exception("legacy"))
            module._create_primary_binding = lambda **kwargs: observed.update(kwargs) or "DB-0003"
            frappe.db.get_value = lambda doctype, filters=None, fieldname=None, as_dict=False: None

            module.execute()

            self.assertEqual(observed["binding_role"], "general_reference")
            self.assertEqual(observed["drive_file_id"], "DF-0003")

    def test_execute_skips_missing_binding_target_without_failing_migrate(self):
        with _patch_module() as (module, frappe):
            module._load_candidate_drive_files = lambda: [
                {
                    "name": "DF-0004",
                    "file": "FILE-0004",
                    "source_upload_session": "DUS-0001",
                    "status": "active",
                    "attached_doctype": "Supporting Material",
                    "attached_name": "MAT-MISSING",
                    "owner_doctype": "Supporting Material",
                    "owner_name": "MAT-MISSING",
                    "slot": "resource",
                }
            ]
            module._resolve_binding_role = lambda upload_session_doc: "general_reference"
            created = []
            logs = []
            module._create_primary_binding = lambda **kwargs: created.append(kwargs) or "DB-0004"
            frappe.db.get_value = lambda doctype, filters=None, fieldname=None, as_dict=False: None
            frappe.db.exists = lambda doctype, name: False
            frappe.log_error = lambda message, title=None: logs.append((title, message))

            module.execute()

            self.assertEqual(created, [])
            self.assertTrue(any(title == "Drive Binding Backfill Skipped" for title, _message in logs))
