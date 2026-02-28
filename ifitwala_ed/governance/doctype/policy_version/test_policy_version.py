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


class TestPolicyVersionAmendments(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.created: list[tuple[str, str]] = []

        self.organization = self._make_organization("PV Amend Org")
        self.school = self._make_school(self.organization, "PV Amend School")
        self.policy = self._make_policy(
            organization=self.organization,
            school=self.school,
            policy_key_prefix="amend_policy",
        )
        self.staff_user = make_user(
            email=f"pv-amend-{frappe.generate_hash(length=8)}@ifitwala.test",
            roles=["Academic Staff"],
        )
        self.created.append(("User", self.staff_user.name))
        self.employee = self._make_employee(self.staff_user.name)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self.created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def test_first_policy_version_allows_blank_amended_from(self):
        version = self._make_policy_version(
            policy=self.policy.name,
            version_label="v1",
            policy_text="<p>Initial staff policy text.</p>",
            is_active=0,
        )
        self.assertFalse(version.based_on_version)
        self.assertFalse(version.diff_html)
        self.assertFalse(version.change_stats)

    def test_new_policy_version_requires_amended_from_after_first(self):
        self._make_policy_version(
            policy=self.policy.name,
            version_label="v1",
            policy_text="<p>Initial policy text.</p>",
            is_active=0,
        )

        with self.assertRaises(frappe.ValidationError):
            self._make_policy_version(
                policy=self.policy.name,
                version_label="v2",
                policy_text="<p>Amended policy text.</p>",
                is_active=0,
            )

    def test_change_summary_required_for_amendment(self):
        base = self._make_policy_version(
            policy=self.policy.name,
            version_label="v1",
            policy_text="<p>Initial policy text.</p>",
            is_active=0,
        )

        with self.assertRaises(frappe.ValidationError):
            self._make_policy_version(
                policy=self.policy.name,
                version_label="v2",
                policy_text="<p>Initial policy text.</p><p>Added detail.</p>",
                is_active=0,
                based_on_version=base.name,
            )

    def test_amended_version_generates_diff_and_stats(self):
        base = self._make_policy_version(
            policy=self.policy.name,
            version_label="v1",
            policy_text="<p>Initial policy text.</p>",
            is_active=0,
        )

        amended = self._make_policy_version(
            policy=self.policy.name,
            version_label="v2",
            policy_text="<p>Initial policy text updated.</p><p>Added new section.</p>",
            is_active=0,
            based_on_version=base.name,
            change_summary="Updated opening paragraph and added a new section.",
        )

        self.assertIn("policy-diff", amended.diff_html or "")
        stats = frappe.parse_json(amended.change_stats or "{}") or {}
        self.assertIsInstance(stats, dict)
        self.assertGreaterEqual(int(stats.get("added") or 0) + int(stats.get("modified") or 0), 1)

    def test_amended_from_must_match_same_policy(self):
        policy_two = self._make_policy(
            organization=self.organization,
            school=self.school,
            policy_key_prefix="other_policy",
        )
        base_one = self._make_policy_version(
            policy=self.policy.name,
            version_label="v1",
            policy_text="<p>Policy one text.</p>",
            is_active=0,
        )
        self._make_policy_version(
            policy=policy_two.name,
            version_label="v1",
            policy_text="<p>Policy two text.</p>",
            is_active=0,
        )

        with self.assertRaises(frappe.ValidationError):
            self._make_policy_version(
                policy=policy_two.name,
                version_label="v2",
                policy_text="<p>Policy two amended text.</p>",
                is_active=0,
                based_on_version=base_one.name,
                change_summary="Cross-policy link should fail.",
            )

    def test_policy_text_can_change_while_draft_without_ack(self):
        version = self._make_policy_version(
            policy=self.policy.name,
            version_label="v1",
            policy_text="<p>Draft text one.</p>",
            is_active=0,
        )

        version.policy_text = "<p>Draft text two.</p>"
        version.save(ignore_permissions=True)
        self.assertEqual(version.policy_text, "<p>Draft text two.</p>")
        self.assertEqual(int(version.text_locked or 0), 0)

    def test_policy_text_locks_after_activation(self):
        version = self._make_policy_version(
            policy=self.policy.name,
            version_label="v1",
            policy_text="<p>Draft text.</p>",
            is_active=0,
        )

        version.is_active = 1
        version.save(ignore_permissions=True)
        self.assertEqual(int(version.text_locked or 0), 1)

        version.policy_text = "<p>Edited after activation.</p>"
        with self.assertRaises(frappe.ValidationError):
            version.save(ignore_permissions=True)

    def test_policy_text_locks_after_acknowledgement(self):
        version = self._make_policy_version(
            policy=self.policy.name,
            version_label="v1",
            policy_text="<p>Active text.</p>",
            is_active=1,
        )

        ack = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": version.name,
                "acknowledged_by": self.staff_user.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee.name,
            }
        )
        frappe.set_user(self.staff_user.name)
        ack.insert(ignore_permissions=True)
        frappe.set_user("Administrator")
        self.created.append(("Policy Acknowledgement", ack.name))

        version.is_active = 0
        version.save(ignore_permissions=True)
        self.assertEqual(int(version.text_locked or 0), 1)

        version.policy_text = "<p>Edited after acknowledgement.</p>"
        with self.assertRaises(frappe.ValidationError):
            version.save(ignore_permissions=True)

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
    ) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{name_prefix}-{frappe.generate_hash(length=8)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        )
        doc.insert(ignore_permissions=True)
        self.created.append(("School", doc.name))
        return doc.name

    def _make_policy(self, *, organization: str, school: str, policy_key_prefix: str):
        doc = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"{policy_key_prefix}_{frappe.generate_hash(length=8)}",
                "policy_title": "Staff Policy",
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

    def _make_employee(self, user: str):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Policy",
                "employee_last_name": f"Policy-{frappe.generate_hash(length=5)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
                "organization": self.organization,
                "school": self.school,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee", employee.name))
        return employee

    def _make_policy_version(
        self,
        *,
        policy: str,
        version_label: str,
        policy_text: str,
        is_active: int,
        based_on_version: str | None = None,
        change_summary: str | None = None,
    ):
        doc = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": policy,
                "version_label": version_label,
                "policy_text": policy_text,
                "is_active": is_active,
                "based_on_version": based_on_version,
                "change_summary": change_summary,
            }
        )
        doc.insert(ignore_permissions=True)
        self.created.append(("Policy Version", doc.name))
        return doc
