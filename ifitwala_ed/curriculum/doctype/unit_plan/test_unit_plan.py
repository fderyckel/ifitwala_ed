# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.curriculum import planning
from ifitwala_ed.curriculum.doctype.unit_plan.unit_plan import get_program_subtree_scope


class TestUnitPlan(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_get_program_subtree_scope_includes_descendants(self):
        parent = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"MYP {frappe.generate_hash(length=6)}",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        child_one = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"MYP1 {frappe.generate_hash(length=6)}",
                "parent_program": parent.name,
            }
        ).insert(ignore_permissions=True)
        child_two = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"MYP2 {frappe.generate_hash(length=6)}",
                "parent_program": parent.name,
            }
        ).insert(ignore_permissions=True)

        scope = get_program_subtree_scope(parent.name)

        self.assertEqual(scope[0], parent.name)
        self.assertIn(child_one.name, scope)
        self.assertIn(child_two.name, scope)

    def test_get_program_subtree_scope_for_leaf_returns_self_only(self):
        leaf = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Leaf Program {frappe.generate_hash(length=6)}",
            }
        ).insert(ignore_permissions=True)

        self.assertEqual(get_program_subtree_scope(leaf.name), [leaf.name])

    def test_ensure_linked_unit_plan_standards_rewrites_snapshot_from_catalog(self):
        standard = frappe.get_doc(
            {
                "doctype": "Learning Standards",
                "framework_name": "IB MYP",
                "program": f"MYP {frappe.generate_hash(length=6)}",
                "strand": "Inquiry",
                "substrand": "Research",
                "standard_code": f"STD-{frappe.generate_hash(length=5)}",
                "standard_description": "Plan and carry out a guided investigation.",
                "alignment_type": "Skill",
            }
        ).insert(ignore_permissions=True)

        class FakeUnitDoc:
            def __init__(self, rows):
                self.standards = rows

            def get(self, fieldname):
                return getattr(self, fieldname)

            def set(self, fieldname, value):
                setattr(self, fieldname, value)

        doc = FakeUnitDoc(
            [
                {
                    "learning_standard": standard.name,
                    "framework_name": "Wrong Value",
                    "standard_code": "WRONG",
                    "coverage_level": "Introduced",
                    "alignment_strength": "Exact",
                    "notes": "Use during the first lab.",
                }
            ]
        )

        planning.ensure_linked_unit_plan_standards(doc)

        self.assertEqual(len(doc.standards), 1)
        self.assertEqual(doc.standards[0]["learning_standard"], standard.name)
        self.assertEqual(doc.standards[0]["framework_name"], "IB MYP")
        self.assertEqual(doc.standards[0]["standard_code"], standard.standard_code)
        self.assertEqual(doc.standards[0]["alignment_type"], "Skill")
        self.assertEqual(doc.standards[0]["coverage_level"], "Introduced")
        self.assertEqual(doc.standards[0]["alignment_strength"], "Exact")
        self.assertEqual(doc.standards[0]["notes"], "Use during the first lab.")

    def test_ensure_linked_unit_plan_standards_rejects_duplicate_standard(self):
        standard = frappe.get_doc(
            {
                "doctype": "Learning Standards",
                "framework_name": "Common Core",
                "strand": "Reading",
                "standard_code": f"CC-{frappe.generate_hash(length=5)}",
                "standard_description": "Quote textual evidence to support analysis.",
            }
        ).insert(ignore_permissions=True)

        class FakeUnitDoc:
            def __init__(self, rows):
                self.standards = rows

            def get(self, fieldname):
                return getattr(self, fieldname)

            def set(self, fieldname, value):
                setattr(self, fieldname, value)

        doc = FakeUnitDoc(
            [
                {"learning_standard": standard.name, "coverage_level": "Introduced"},
                {"learning_standard": standard.name, "coverage_level": "Reinforced"},
            ]
        )

        with self.assertRaises(frappe.ValidationError):
            planning.ensure_linked_unit_plan_standards(doc)

    def test_ensure_linked_unit_plan_standards_falls_back_to_direct_identifier_resolution(self):
        standard = frappe.get_doc(
            {
                "doctype": "Learning Standards",
                "framework_name": "NGSS",
                "strand": "Life Science",
                "standard_code": f"NG-{frappe.generate_hash(length=5)}",
                "standard_description": "Develop a model to describe cell function.",
                "alignment_type": "Knowledge",
            }
        ).insert(ignore_permissions=True)

        class FakeUnitDoc:
            def __init__(self, rows):
                self.standards = rows

            def get(self, fieldname):
                return getattr(self, fieldname)

            def set(self, fieldname, value):
                setattr(self, fieldname, value)

        doc = FakeUnitDoc(
            [
                {
                    "learning_standard": standard.name,
                    "coverage_level": "Introduced",
                }
            ]
        )

        original_get_all = frappe.get_all

        def fake_get_all(doctype, *args, **kwargs):
            if doctype == "Learning Standards" and kwargs.get("filters") == {"name": ["in", [standard.name]]}:
                return []
            return original_get_all(doctype, *args, **kwargs)

        with patch.object(frappe, "get_all", side_effect=fake_get_all):
            planning.ensure_linked_unit_plan_standards(doc)

        self.assertEqual(doc.standards[0]["learning_standard"], standard.name)
        self.assertEqual(doc.standards[0]["standard_code"], standard.standard_code)

    def test_ensure_linked_unit_plan_standards_falls_back_to_snapshot_match_when_identifier_fails(self):
        standard = frappe.get_doc(
            {
                "doctype": "Learning Standards",
                "framework_name": "IB MYP",
                "program": f"MYP {frappe.generate_hash(length=6)}",
                "strand": "Identity",
                "substrand": "Narrative",
                "standard_code": f"MYP-{frappe.generate_hash(length=5)}",
                "standard_description": "Analyze how narrative voice shapes meaning.",
                "alignment_type": "Skill",
            }
        ).insert(ignore_permissions=True)

        class FakeUnitDoc:
            def __init__(self, rows):
                self.standards = rows

            def get(self, fieldname):
                return getattr(self, fieldname)

            def set(self, fieldname, value):
                setattr(self, fieldname, value)

        doc = FakeUnitDoc(
            [
                {
                    "learning_standard": "broken-link-value",
                    "framework_name": standard.framework_name,
                    "program": standard.program,
                    "strand": standard.strand,
                    "substrand": standard.substrand,
                    "standard_code": standard.standard_code,
                    "standard_description": standard.standard_description,
                    "alignment_type": standard.alignment_type,
                    "coverage_level": "Introduced",
                }
            ]
        )

        planning.ensure_linked_unit_plan_standards(doc)

        self.assertEqual(doc.standards[0]["learning_standard"], standard.name)
        self.assertEqual(doc.standards[0]["standard_code"], standard.standard_code)
        self.assertEqual(doc.standards[0]["coverage_level"], "Introduced")
