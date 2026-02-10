# ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py
# Copyright (c) 2024, fdR and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from ifitwala_ed.admission.doctype.student_applicant.student_applicant import academic_year_intent_query


class TestStudentApplicant(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._created = []
		self._ensure_admissions_role("Administrator", "Admission Manager")
		self.org = self._create_org()
		self.parent_school = self._create_school("Admissions Root", "AR", self.org, is_group=1)
		self.leaf_school = self._create_school("Admissions Leaf", "AL", self.org, parent=self.parent_school, is_group=0)

		self.visible_ay = self._create_academic_year(self.leaf_school, "2025-2026", archived=0, visible=1)
		self.archived_ay = self._create_academic_year(self.leaf_school, "2024-2025", archived=1, visible=1)
		self.hidden_ay = self._create_academic_year(self.leaf_school, "2023-2024", archived=0, visible=0)

	def tearDown(self):
		for doctype, name in reversed(self._created):
			if frappe.db.exists(doctype, name):
				frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

	def test_academic_year_query_filters_visibility(self):
		rows = academic_year_intent_query(
			"Academic Year",
			"",
			"name",
			0,
			50,
			{"school": self.leaf_school},
		)
		names = {r[0] for r in rows}
		self.assertIn(self.visible_ay, names)
		self.assertNotIn(self.archived_ay, names)
		self.assertNotIn(self.hidden_ay, names)

	def test_academic_year_query_scope_leaf_ancestor(self):
		orphan_leaf = self._create_school("Orphan Leaf", "OL", self.org, parent=self.parent_school, is_group=0)
		parent_ay = self._create_academic_year(self.parent_school, "2026-2027", archived=0, visible=1)
		rows = academic_year_intent_query(
			"Academic Year",
			"",
			"name",
			0,
			50,
			{"school": orphan_leaf},
		)
		names = {r[0] for r in rows}
		self.assertIn(parent_ay, names)

	def test_academic_year_query_scope_non_leaf_child_ancestor(self):
		intermediate_school = self._create_school("Intermediate School", "IS", self.org, parent=self.parent_school, is_group=1)
		self._create_school("Intermediate Leaf A", "IA", self.org, parent=intermediate_school, is_group=0)
		self._create_school("Intermediate Leaf B", "IB", self.org, parent=intermediate_school, is_group=0)
		parent_ay = self._create_academic_year(self.parent_school, "2027-2028", archived=0, visible=1)

		rows = academic_year_intent_query(
			"Academic Year",
			"",
			"name",
			0,
			50,
			{"school": intermediate_school},
		)
		names = {r[0] for r in rows}
		self.assertIn(parent_ay, names)

	def test_validation_blocks_archived_ay(self):
		applicant = frappe.get_doc({
			"doctype": "Student Applicant",
			"first_name": "Test",
			"last_name": "Applicant",
			"organization": self.org,
			"school": self.leaf_school,
			"academic_year": self.archived_ay,
			"application_status": "Draft",
		})
		with self.assertRaises(frappe.ValidationError):
			applicant.insert(ignore_permissions=True)

	def _ensure_admissions_role(self, user, role):
		if not frappe.db.exists("Role", role):
			return
		if not frappe.db.exists("Has Role", {"parent": user, "role": role}):
			frappe.get_doc({
				"doctype": "Has Role",
				"parent": user,
				"parenttype": "User",
				"parentfield": "roles",
				"role": role,
			}).insert(ignore_permissions=True)

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

	def _create_academic_year(self, school, academic_year_name, archived=0, visible=1):
		doc = frappe.get_doc({
			"doctype": "Academic Year",
			"academic_year_name": academic_year_name,
			"school": school,
			"archived": archived,
			"visible_to_admission": visible,
		}).insert(ignore_permissions=True)
		self._created.append(("Academic Year", doc.name))
		return doc.name
