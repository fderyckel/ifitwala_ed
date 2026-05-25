from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.patches.repair_core_contacts_module_ownership import repair_core_contacts_module_ownership


class _FakeModuleDef:
    def __init__(self):
        self.insert = Mock()


class TestRepairCoreContactsModuleOwnership(TestCase):
    def test_repairs_stale_ifitwala_contacts_module_ownership(self):
        db = SimpleNamespace()
        db.exists = Mock(return_value=True)
        db.get_value = Mock(return_value="ifitwala_ed")
        db.set_value = Mock()
        frappe = SimpleNamespace(db=db)

        repair_core_contacts_module_ownership(frappe)

        db.exists.assert_called_once_with("Module Def", "Contacts")
        db.set_value.assert_called_once_with(
            "Module Def",
            "Contacts",
            "app_name",
            "frappe",
            update_modified=False,
        )

    def test_leaves_core_frappe_contacts_module_ownership_alone(self):
        db = SimpleNamespace()
        db.exists = Mock(return_value=True)
        db.get_value = Mock(return_value="frappe")
        db.set_value = Mock()
        frappe = SimpleNamespace(db=db)

        repair_core_contacts_module_ownership(frappe)

        db.set_value.assert_not_called()

    def test_recreates_missing_core_contacts_module_def(self):
        db = SimpleNamespace()
        db.exists = Mock(return_value=False)
        db.get_value = Mock()
        db.set_value = Mock()
        module_def = _FakeModuleDef()
        frappe = SimpleNamespace(db=db, get_doc=Mock(return_value=module_def))

        repair_core_contacts_module_ownership(frappe)

        frappe.get_doc.assert_called_once_with(
            {
                "doctype": "Module Def",
                "module_name": "Contacts",
                "app_name": "frappe",
            }
        )
        module_def.insert.assert_called_once_with(ignore_permissions=True)
