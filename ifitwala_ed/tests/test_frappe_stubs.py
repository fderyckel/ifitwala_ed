from __future__ import annotations

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
