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
        yield import_fresh("ifitwala_ed.patches.remove_file_classification_rows"), frappe


class TestRemoveFileClassificationRows(TestCase):
    def test_execute_deletes_classifications_only_after_drive_authority_exists(self):
        rows = [
            {"name": "FC-0001", "file": "FILE-0001"},
            {"name": "FC-0002", "file": "FILE-0002"},
        ]

        with _patch_module() as (module, frappe):
            frappe.db.table_exists = lambda doctype: (
                doctype
                in {
                    "File Classification",
                    "Drive File",
                    "File Classification Subject",
                }
            )
            frappe.get_all = Mock(return_value=rows)
            frappe.db.exists = lambda doctype, filters=None: (
                doctype == "Drive File"
                and filters
                in (
                    {"file": "FILE-0001"},
                    {"file": "FILE-0002"},
                )
            )
            frappe.db.delete = Mock()

            module.execute()

        frappe.get_all.assert_called_once_with(
            "File Classification",
            fields=["name", "file"],
            limit=100000,
        )
        frappe.db.delete.assert_any_call(
            "File Classification Subject",
            {"parenttype": "File Classification", "parent": ["in", ["FC-0001", "FC-0002"]]},
        )
        frappe.db.delete.assert_any_call("File Classification", {"name": ["in", ["FC-0001", "FC-0002"]]})

    def test_execute_throws_when_drive_authority_is_missing(self):
        with _patch_module() as (module, frappe):
            frappe.db.table_exists = lambda doctype: doctype in {"File Classification", "Drive File"}
            frappe.get_all = Mock(return_value=[{"name": "FC-0001", "file": "FILE-0001"}])
            frappe.db.exists = Mock(return_value=False)

            with self.assertRaisesRegex(Exception, "Missing Drive File coverage for: FILE-0001"):
                module.execute()
