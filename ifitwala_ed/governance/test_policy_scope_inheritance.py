# ifitwala_ed/governance/test_policy_scope_inheritance.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.governance.policy_utils import has_applicant_policy_acknowledgement


class TestPolicyScopeInheritance(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_parent_policy_scope_allows_descendant_school(self):
        parent_org = self._make_organization("Parent", is_group=1)
        child_org = self._make_organization("Child", parent=parent_org)
        child_school = self._make_school(child_org, "Child School")

        policy = self._make_policy(
            organization=parent_org,
            policy_key=self._policy_key("descendant_allow"),
            school=child_school,
        )
        self.assertEqual(policy.school, child_school)

    def test_parent_policy_is_required_for_descendant_applicant_and_sibling_isolation(self):
        parent_org = self._make_organization("Parent", is_group=1)
        child_org = self._make_organization("Child", parent=parent_org)
        sibling_org = self._make_organization("Sibling", parent=parent_org)
        child_school = self._make_school(child_org, "Child School")
        applicant = self._make_applicant(child_org, child_school)

        parent_key = self._policy_key("parent_applies")
        sibling_key = self._policy_key("sibling_isolated")

        self._make_active_policy_with_version(
            organization=parent_org,
            policy_key=parent_key,
            version_label="v1-parent",
        )
        self._make_active_policy_with_version(
            organization=sibling_org,
            policy_key=sibling_key,
            version_label="v1-sibling",
        )

        status = applicant.has_required_policies()
        self.assertIn(parent_key, status["required"])
        self.assertNotIn(sibling_key, status["required"])

    def test_nearest_override_requires_child_ack_when_same_policy_key_exists(self):
        parent_org = self._make_organization("Parent", is_group=1)
        child_org = self._make_organization("Child", parent=parent_org)
        child_school = self._make_school(child_org, "Child School")
        applicant = self._make_applicant(child_org, child_school)

        shared_key = self._policy_key("nearest_override")
        parent_policy, parent_version = self._make_active_policy_with_version(
            organization=parent_org,
            policy_key=shared_key,
            version_label="v1-parent",
        )
        child_policy, child_version = self._make_active_policy_with_version(
            organization=child_org,
            policy_key=shared_key,
            version_label="v1-child",
        )

        self.assertIsNotNone(parent_policy)
        self.assertIsNotNone(child_policy)

        self.assertFalse(
            has_applicant_policy_acknowledgement(
                policy_key=shared_key,
                student_applicant=applicant.name,
                organization=child_org,
                school=child_school,
            )
        )

        self._acknowledge(applicant_name=applicant.name, policy_version=parent_version.name)
        self.assertFalse(
            has_applicant_policy_acknowledgement(
                policy_key=shared_key,
                student_applicant=applicant.name,
                organization=child_org,
                school=child_school,
            )
        )

        self._acknowledge(applicant_name=applicant.name, policy_version=child_version.name)
        self.assertTrue(
            has_applicant_policy_acknowledgement(
                policy_key=shared_key,
                student_applicant=applicant.name,
                organization=child_org,
                school=child_school,
            )
        )

    def test_unrelated_policy_is_blocked_for_descendant_applicant(self):
        parent_org = self._make_organization("Parent", is_group=1)
        child_org = self._make_organization("Child", parent=parent_org)
        unrelated_org = self._make_organization("Unrelated", is_group=1)
        child_school = self._make_school(child_org, "Child School")
        unrelated_school = self._make_school(unrelated_org, "Unrelated School")
        applicant = self._make_applicant(child_org, child_school)

        unrelated_policy, unrelated_version = self._make_active_policy_with_version(
            organization=unrelated_org,
            policy_key=self._policy_key("unrelated_block"),
            school=unrelated_school,
            version_label="v1-unrelated",
        )
        self.assertIsNotNone(unrelated_policy)

        with self.assertRaises(frappe.ValidationError):
            self._acknowledge(applicant_name=applicant.name, policy_version=unrelated_version.name)

    def test_school_can_be_set_once_when_initially_blank(self):
        org = self._make_organization("Org")
        first_school = self._make_school(org, "First School")
        second_school = self._make_school(org, "Second School")

        policy = self._make_policy(
            organization=org,
            policy_key=self._policy_key("one_time_school"),
            school=None,
        )
        self.assertFalse(policy.school)

        policy.school = first_school
        policy.save(ignore_permissions=True)
        self.assertEqual(policy.school, first_school)

        policy.school = second_school
        with self.assertRaises(frappe.ValidationError):
            policy.save(ignore_permissions=True)

    def test_parent_school_policy_applies_to_descendant_school_applicant(self):
        org = self._make_organization("Org")
        parent_school = self._make_school(org, "Parent School", is_group=1)
        child_school = self._make_school(org, "Child School", parent_school=parent_school)
        applicant = self._make_applicant(org, child_school)
        policy_key = self._policy_key("school_descendant_scope")

        self._make_active_policy_with_version(
            organization=org,
            policy_key=policy_key,
            school=parent_school,
            version_label="v1-parent-school",
        )

        status = applicant.has_required_policies()
        self.assertIn(policy_key, status["required"])

    def test_school_scoped_policy_does_not_apply_outside_school_lineage(self):
        org = self._make_organization("Org")
        root_school = self._make_school(org, "Root School", is_group=1)
        sibling_a = self._make_school(org, "Sibling A", parent_school=root_school)
        sibling_b = self._make_school(org, "Sibling B", parent_school=root_school)
        applicant = self._make_applicant(org, sibling_b)
        policy_key = self._policy_key("school_lineage_only")

        self._make_active_policy_with_version(
            organization=org,
            policy_key=policy_key,
            school=sibling_a,
            version_label="v1-sibling-a",
        )

        status = applicant.has_required_policies()
        self.assertNotIn(policy_key, status["required"])

    def _policy_key(self, prefix: str) -> str:
        return f"{prefix}_{frappe.generate_hash(length=8)}"

    def _make_organization(self, prefix: str, parent: str | None = None, is_group: int = 0) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix}-{frappe.generate_hash(length=8)}",
                "abbr": f"O{frappe.generate_hash(length=5)}",
                "is_group": int(is_group),
                "parent_organization": parent,
            }
        )
        doc.insert(ignore_permissions=True)
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
                "school_name": f"{name_prefix}-{frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
                "parent_school": parent_school,
                "is_group": int(is_group),
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_policy(self, organization: str, policy_key: str, school: str | None = None):
        doc = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": policy_key,
                "policy_title": f"Policy {policy_key}",
                "policy_category": "Admissions",
                "applies_to": "Applicant",
                "organization": organization,
                "school": school,
                "is_active": 1,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def _make_active_policy_with_version(
        self,
        *,
        organization: str,
        policy_key: str,
        version_label: str,
        school: str | None = None,
    ):
        policy = self._make_policy(organization=organization, policy_key=policy_key, school=school)
        version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": policy.name,
                "version_label": version_label,
                "policy_text": f"<p>{policy_key} {version_label}</p>",
                "is_active": 1,
            }
        )
        version.insert(ignore_permissions=True)
        return policy, version

    def _make_applicant(self, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Policy",
                "last_name": f"Applicant-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def _acknowledge(self, *, applicant_name: str, policy_version: str):
        doc = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": policy_version,
                "acknowledged_by": frappe.session.user,
                "acknowledged_for": "Applicant",
                "context_doctype": "Student Applicant",
                "context_name": applicant_name,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc
