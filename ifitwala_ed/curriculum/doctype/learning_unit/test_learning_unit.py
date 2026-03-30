# Copyright (c) 2024, fdR and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.curriculum.doctype.learning_unit.learning_unit import get_program_subtree_scope


class TestLearningUnit(FrappeTestCase):
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
