from __future__ import annotations

import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestFrappeStubs(TestCase):
    def test_stubbed_frappe_removes_leaked_parent_package_attrs_from_extra_modules(self):
        with TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "stubpkg"
            package_root.mkdir()
            (package_root / "__init__.py").write_text("__all__ = []\n", encoding="utf-8")
            (package_root / "subpkg.py").write_text("VALUE = 'real'\n", encoding="utf-8")
            sys.path.insert(0, temp_dir)
            try:
                root_package = __import__("stubpkg")
                self.assertFalse(hasattr(root_package, "subpkg"))

                fake_leaf = ModuleType("stubpkg.subpkg.fake_leaf")

                with stubbed_frappe(extra_modules={"stubpkg.subpkg.fake_leaf": fake_leaf}):
                    import_fresh("stubpkg.subpkg")
                    self.assertTrue(hasattr(root_package, "subpkg"))

                self.assertFalse(hasattr(root_package, "subpkg"))
                self.assertNotIn("stubpkg.subpkg", sys.modules)
                self.assertNotIn("stubpkg.subpkg.fake_leaf", sys.modules)
            finally:
                sys.modules.pop("stubpkg.subpkg.fake_leaf", None)
                sys.modules.pop("stubpkg.subpkg", None)
                sys.modules.pop("stubpkg", None)
                sys.path.remove(temp_dir)

    def test_stubbed_frappe_removes_preexisting_stub_bound_controller_module(self):
        module_name = "ifitwala_ed.governance.doctype.contact_access_log.contact_access_log"
        parent_name = "ifitwala_ed.governance.doctype.contact_access_log"
        attr_name = "contact_access_log"

        with stubbed_frappe():
            leaked_module = import_fresh(module_name)

        parent_module = importlib.import_module(parent_name)
        sys.modules[module_name] = leaked_module
        setattr(parent_module, attr_name, leaked_module)

        try:
            with stubbed_frappe():
                self.assertIs(sys.modules[module_name], leaked_module)

            self.assertNotIn(module_name, sys.modules)
            self.assertFalse(hasattr(parent_module, attr_name))
        finally:
            if getattr(parent_module, attr_name, None) is leaked_module:
                delattr(parent_module, attr_name)
            sys.modules.pop(module_name, None)

    def test_import_fresh_does_not_restore_previous_stub_bound_module(self):
        module_name = "ifitwala_ed.governance.doctype.contact_access_log.contact_access_log"

        with stubbed_frappe():
            leaked_module = import_fresh(module_name)

        sys.modules[module_name] = leaked_module
        try:
            with stubbed_frappe():
                import_fresh(module_name)

            self.assertNotIn(module_name, sys.modules)
        finally:
            sys.modules.pop(module_name, None)
