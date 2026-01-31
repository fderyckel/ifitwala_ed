# ifitwala_ed/utilities/test_school_tree.py

import frappe
from frappe.tests.utils import FrappeTestCase
from ifitwala_ed.utilities.school_tree import get_school_scope_for_academic_year


class TestSchoolTreeScopes(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._created = []
		self.org = self._create_org()
		self.root_school = self._create_school("Scope Root", "SR", self.org, is_group=1)
		self.child_school = self._create_school("Scope Child", "SC", self.org, parent=self.root_school, is_group=1)
		self.leaf_school = self._create_school("Scope Leaf", "SL", self.org, parent=self.child_school, is_group=0)

	def tearDown(self):
		for doctype, name in reversed(self._created):
			if frappe.db.exists(doctype, name):
				frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

	def test_leaf_scope_uses_nearest_ancestor(self):
		ancestor_ay = self._create_academic_year(self.root_school, "2026-2027")
		self._clear_scope_cache(self.leaf_school)
		scope = get_school_scope_for_academic_year(self.leaf_school)
		self.assertEqual(scope, [self.root_school])
		self.assertTrue(frappe.db.exists("Academic Year", ancestor_ay))

	def test_parent_scope_includes_descendants(self):
		self._clear_scope_cache(self.root_school)
		scope = get_school_scope_for_academic_year(self.root_school)
		self.assertTrue(self.root_school in scope)
		self.assertTrue(self.child_school in scope)
		self.assertTrue(self.leaf_school in scope)

	def test_leaf_scope_prefers_self_when_ay_exists(self):
		self._create_academic_year(self.leaf_school, "2025-2026")
		self._clear_scope_cache(self.leaf_school)
		scope = get_school_scope_for_academic_year(self.leaf_school)
		self.assertEqual(scope, [self.leaf_school])

	def _clear_scope_cache(self, school):
		frappe.cache().delete_value(f"ifitwala_ed:school_tree:ay_scope:{school}")

	def _create_org(self):
		name = f"Org-{frappe.generate_hash(length=6)}"
		doc = frappe.get_doc({
			"doctype": "Organization",
			"organization_name": name,
			"abbr": name[:6].upper(),
		}).insert(ignore_permissions=True)
		self._created.append(("Organization", doc.name))
		return doc.name

	def _create_school(self, school_name, abbr, organization, parent=None, is_group=0):
		doc = frappe.get_doc({
			"doctype": "School",
			"school_name": school_name,
			"abbr": abbr,
			"organization": organization,
			"is_group": 1 if is_group else 0,
			"parent_school": parent,
		}).insert(ignore_permissions=True)
		self._created.append(("School", doc.name))
		return doc.name

	def _create_academic_year(self, school, academic_year_name):
		doc = frappe.get_doc({
			"doctype": "Academic Year",
			"academic_year_name": academic_year_name,
			"school": school,
			"archived": 0,
			"visible_to_admission": 1,
		}).insert(ignore_permissions=True)
		self._created.append(("Academic Year", doc.name))
		return doc.name
