# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt
# ifitwala_ed/governance/doctype/policy_acknowledgement/test_policy_acknowledgement.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.governance.doctype.policy_acknowledgement import policy_acknowledgement as policy_ack_controller
from ifitwala_ed.governance.policy_utils import ensure_policy_audience_records
from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.tests.factories.users import make_user


class TestPolicyAcknowledgement(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        ensure_policy_audience_records()
        self.created: list[tuple[str, str]] = []

        self.organization = make_organization(prefix="PA Org")
        self.created.append(("Organization", self.organization.name))
        self.school = make_school(self.organization.name, prefix="PA School")
        self.created.append(("School", self.school.name))

        self.staff_user = make_user(roles=["Academic Staff"])
        self.created.append(("User", self.staff_user.name))
        self.employee = self._make_employee(self.staff_user.name)

        self.policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"policy_ack_{frappe.generate_hash(length=8)}",
                "policy_title": "Policy Acknowledgement Lifecycle",
                "policy_category": "Employment",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": self.organization.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", self.policy.name))

        self.policy_version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": self.policy.name,
                "version_label": "v1",
                "policy_text": "<p>Immutable acknowledgement policy text.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", self.policy_version.name))

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self.created):
            self._delete_created_doc(doctype, name)
        super().tearDown()

    def _delete_created_doc(self, doctype: str, name: str):
        if not frappe.db.exists(doctype, name):
            return
        if doctype == "Policy Acknowledgement":
            frappe.db.delete("Policy Acknowledgement", {"name": name})
            return
        frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def _make_employee(self, user: str):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Policy",
                "employee_last_name": f"Ack-{frappe.generate_hash(length=6)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
                "organization": self.organization.name,
                "school": self.school.name,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee", employee.name))
        return employee

    def _insert_staff_ack(self):
        frappe.set_user(self.staff_user.name)
        ack = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": self.policy_version.name,
                "acknowledged_by": self.staff_user.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee.name,
            }
        ).insert(ignore_permissions=True)
        frappe.set_user("Administrator")
        self.created.append(("Policy Acknowledgement", ack.name))
        return ack

    def test_acknowledgement_auto_submits_on_insert(self):
        ack = self._insert_staff_ack()
        self.assertEqual(int(ack.docstatus or 0), 1)
        self.assertTrue(bool(ack.acknowledged_at))

    def test_submitted_acknowledgement_cannot_be_edited(self):
        ack = self._insert_staff_ack()
        ack.context_name = self.employee.name

        with self.assertRaises(frappe.ValidationError):
            ack.save(ignore_permissions=True)

    def test_submitted_acknowledgement_cannot_be_cancelled(self):
        ack = self._insert_staff_ack()
        with self.assertRaises(frappe.ValidationError):
            ack.cancel()

    def test_duplicate_acknowledgement_still_rejected(self):
        self._insert_staff_ack()

        frappe.set_user(self.staff_user.name)
        duplicate = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": self.policy_version.name,
                "acknowledged_by": self.staff_user.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee.name,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            duplicate.insert(ignore_permissions=True)
        frappe.set_user("Administrator")

    def test_guardian_context_organizations_include_student_applicant_links(self):
        doc = policy_ack_controller.PolicyAcknowledgement.__new__(policy_ack_controller.PolicyAcknowledgement)
        doc.context_doctype = "Guardian"
        doc.context_name = "GUARD-1"

        def fake_get_all(doctype, **kwargs):
            if doctype == "Student Guardian":
                return []
            if doctype == "Student Applicant Guardian":
                return ["APPL-1", "APPL-2"]
            if doctype == "Student Applicant":
                return ["ORG-1", "ORG-1", "ORG-2"]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with (
            patch.object(doc, "_organizations_for_students", return_value=[]),
            patch(
                "ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement.frappe.get_all",
                side_effect=fake_get_all,
            ),
        ):
            orgs = doc._resolve_context_organizations()

        self.assertEqual(orgs, ["ORG-1", "ORG-2"])
