from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest import TestCase


def _controller_class_name(doctype_name: str) -> str:
    return "".join(doctype_name.replace("-", " ").replace("_", " ").split())


class TestDocTypePackageShape(TestCase):
    def _package_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _doctype_json_paths(self):
        return sorted(self._package_root().glob("*/doctype/*/*.json"))

    def test_every_doctype_has_package_init_controller_and_matching_class(self):
        violations: list[str] = []

        for json_path in self._doctype_json_paths():
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            if payload.get("doctype") != "DocType":
                continue

            doctype_name = payload.get("name") or json_path.stem.replace("_", " ").title()
            expected_class = _controller_class_name(doctype_name)
            init_path = json_path.parent / "__init__.py"
            py_path = json_path.with_suffix(".py")

            if not init_path.exists():
                violations.append(f"{json_path}: missing __init__.py")
                continue
            if not py_path.exists():
                violations.append(f"{json_path}: missing {json_path.stem}.py")
                continue

            tree = ast.parse(py_path.read_text(encoding="utf-8"))
            matching_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == expected_class:
                    matching_class = node
                    break

            if matching_class is None:
                violations.append(f"{py_path}: missing class {expected_class}")
                continue
            if not matching_class.bases:
                violations.append(f"{py_path}: class {expected_class} must inherit a Frappe controller base")

        self.assertEqual(violations, [])

    def test_ifitwala_ed_does_not_claim_frappe_core_contacts_module(self):
        package_root = self._package_root()
        app_modules = package_root.joinpath("modules.txt").read_text(encoding="utf-8").splitlines()
        self.assertNotIn("Contacts", app_modules)

        contact_module_doctypes: list[str] = []
        for json_path in self._doctype_json_paths():
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            if payload.get("doctype") == "DocType" and payload.get("module") == "Contacts":
                contact_module_doctypes.append(str(json_path.relative_to(package_root)))

        self.assertEqual(contact_module_doctypes, [])
