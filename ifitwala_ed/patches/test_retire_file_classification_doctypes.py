from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _patch_module():
    with stubbed_frappe() as frappe:
        frappe.db = SimpleNamespace()
        frappe.delete_doc = Mock()
        yield import_fresh("ifitwala_ed.patches.retire_file_classification_doctypes"), frappe


class TestRetireFileClassificationDoctypes(TestCase):
    def test_execute_deletes_legacy_doctypes_once_runtime_rows_are_gone(self):
        with _patch_module() as (module, frappe):
            frappe.db.table_exists = lambda doctype: doctype in {"File Classification", "File Classification Subject"}
            frappe.db.count = lambda doctype: 0
            frappe.get_all = Mock(return_value=[])
            frappe.db.exists = lambda doctype, name=None: (
                doctype == "DocType"
                and name
                in {
                    "File Classification Subject",
                    "File Classification",
                }
            )

            module.execute()

        frappe.delete_doc.assert_any_call(
            "DocType",
            "File Classification Subject",
            force=True,
            ignore_permissions=True,
        )
        frappe.delete_doc.assert_any_call(
            "DocType",
            "File Classification",
            force=True,
            ignore_permissions=True,
        )

    def test_execute_throws_when_file_classification_rows_still_exist(self):
        with _patch_module() as (module, frappe):
            frappe.db.table_exists = lambda doctype: doctype == "File Classification"
            frappe.db.count = lambda doctype: 1

            with self.assertRaisesRegex(Exception, "before all classification rows are removed"):
                module.execute()

    def test_execute_throws_when_non_classification_child_rows_remain(self):
        with _patch_module() as (module, frappe):
            frappe.db.table_exists = lambda doctype: doctype in {"File Classification", "File Classification Subject"}
            frappe.db.count = lambda doctype: 0
            frappe.get_all = Mock(return_value=[{"parenttype": "Drive Upload Session"}])

            with self.assertRaisesRegex(Exception, "Remaining parenttypes: Drive Upload Session"):
                module.execute()
