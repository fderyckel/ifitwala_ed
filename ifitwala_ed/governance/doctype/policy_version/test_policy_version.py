# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt
# ifitwala_ed/governance/doctype/policy_version/test_policy_version.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.governance.doctype.policy_version.policy_version import approved_by_user_query
from ifitwala_ed.tests.factories.users import make_user


class TestPolicyVersionApprovedBy(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.created: list[tuple[str, str]] = []

        self.organization = self._make_organization("PV Org")
        self.root_school = self._make_school(self.organization, "PV Root School", is_group=1)
        self.child_school = self._make_school(self.organization, "PV Child School", parent_school=self.root_school)
        self.sibling_school = self._make_school(self.organization, "PV Sibling School", parent_school=self.root_school)
        self.policy = self._make_policy(
            organization=self.organization,
            school=self.child_school,
        )

        self.child_writer = self._make_user_with_employee(
            role="Organization Admin",
            school=self.child_school,
            prefix="child-writer",
        )
        self.parent_writer = self._make_user_with_employee(
            role="Organization Admin",
            school=self.root_school,
            prefix="parent-writer",
        )
        self.sibling_writer = self._make_user_with_employee(
            role="Organization Admin",
            school=self.sibling_school,
            prefix="sibling-writer",
        )
        self.no_write_user = self._make_user_with_employee(
            role="Employee",
            school=self.child_school,
            prefix="no-write",
        )

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self.created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_approved_by_allows_same_school_and_parent_school_writer(self):
        version = self._make_policy_version(approved_by=self.child_writer)
        self.assertEqual(version.approved_by, self.child_writer)

        version.approved_by = self.parent_writer
        version.save(ignore_permissions=True)
        self.assertEqual(version.approved_by, self.parent_writer)

    def test_approved_by_rejects_sibling_school_writer(self):
        version = self._make_policy_version(approved_by=self.child_writer)
        version.approved_by = self.sibling_writer

        with self.assertRaises(frappe.PermissionError):
            version.save(ignore_permissions=True)

    def test_approved_by_rejects_user_without_write_access(self):
        with self.assertRaises(frappe.PermissionError):
            self._make_policy_version(approved_by=self.no_write_user)

    def test_approved_by_user_query_limits_to_scope_and_write_access(self):
        rows = approved_by_user_query(
            doctype="User",
            txt="",
            searchfield="name",
            start=0,
            page_len=50,
            filters={"institutional_policy": self.policy.name},
        )
        names = {row[0] for row in rows}

        self.assertIn(self.child_writer, names)
        self.assertIn(self.parent_writer, names)
        self.assertNotIn(self.sibling_writer, names)
        self.assertNotIn(self.no_write_user, names)

    def _make_organization(self, prefix: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix}-{frappe.generate_hash(length=8)}",
                "abbr": f"O{frappe.generate_hash(length=5)}",
            }
        )
        doc.insert(ignore_permissions=True)
        self.created.append(("Organization", doc.name))
        return doc.name

    def _make_school(
        self,
        organization: str,
        name_prefix: str,
        parent_school: str | None = None,
        is_group: int = 0,
    ) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{name_prefix}-{frappe.generate_hash(length=8)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
                "parent_school": parent_school,
                "is_group": int(is_group),
            }
        )
        doc.insert(ignore_permissions=True)
        self.created.append(("School", doc.name))
        return doc.name

    def _make_policy(self, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"approved_by_scope_{frappe.generate_hash(length=8)}",
                "policy_title": "Approved By Scope Policy",
                "policy_category": "Operations",
                "applies_to": "Staff",
                "organization": organization,
                "school": school,
                "is_active": 1,
            }
        )
        doc.insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", doc.name))
        return doc

    def _make_user_with_employee(self, *, role: str, school: str, prefix: str) -> str:
        user = make_user(
            email=f"{prefix}-{frappe.generate_hash(length=8)}@ifitwala.test",
            roles=[role],
        )
        self.created.append(("User", user.name))

        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Policy",
                "employee_last_name": f"{prefix}-{frappe.generate_hash(length=5)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user.name,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
                "organization": self.organization,
                "school": school,
                "user_id": user.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee", employee.name))
        return user.name

    def _make_policy_version(self, *, approved_by: str):
        doc = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": self.policy.name,
                "version_label": f"v-{frappe.generate_hash(length=6)}",
                "policy_text": "<p>Approved By scope test policy text.</p>",
                "approved_by": approved_by,
                "is_active": 0,
            }
        )
        doc.insert(ignore_permissions=True)
        self.created.append(("Policy Version", doc.name))
        return doc
