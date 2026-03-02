# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt
# ifitwala_ed/governance/doctype/policy_acknowledgement/test_policy_acknowledgement.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.tests.factories.users import make_user


class TestPolicyAcknowledgement(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
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
                "applies_to": "Staff",
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
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

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
