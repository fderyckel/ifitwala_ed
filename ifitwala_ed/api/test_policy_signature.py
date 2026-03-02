# ifitwala_ed/api/test_policy_signature.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.api.policy_signature import (
    get_staff_policy_signature_dashboard,
    launch_staff_policy_campaign,
)
from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.tests.factories.users import make_user


class TestPolicySignature(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.created: list[tuple[str, str]] = []

        self.organization = make_organization(prefix="PS Org")
        self.created.append(("Organization", self.organization.name))
        self.school = make_school(self.organization.name, prefix="PS School")
        self.created.append(("School", self.school.name))

        self.employee_group = frappe.get_doc(
            {
                "doctype": "Employee Group",
                "employee_group_name": f"PS Group {frappe.generate_hash(length=6)}",
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee Group", self.employee_group.name))

        self.user_one = make_user()
        self.user_two = make_user()
        self.created.extend([("User", self.user_one.name), ("User", self.user_two.name)])

        self.employee_one = self._make_employee(self.user_one.name)
        self.employee_two = self._make_employee(self.user_two.name)

        self.policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"staff_policy_{frappe.generate_hash(length=8)}",
                "policy_title": "Staff Data Handling",
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
                "version_label": "v2",
                "policy_text": "<p>Read and sign this policy.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", self.policy_version.name))

        # Pre-sign one employee to validate pending/signed split.
        frappe.set_user(self.user_one.name)
        ack = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": self.policy_version.name,
                "acknowledged_by": self.user_one.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee_one.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Acknowledgement", ack.name))
        frappe.set_user("Administrator")

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
                "employee_last_name": f"Signer-{frappe.generate_hash(length=5)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
                "organization": self.organization.name,
                "school": self.school.name,
                "employee_group": self.employee_group.name,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee", employee.name))
        return employee

    def test_launch_campaign_counts_and_dashboard(self):
        client_request_id = f"policy-launch-{frappe.generate_hash(length=8)}"
        result = launch_staff_policy_campaign(
            policy_version=self.policy_version.name,
            organization=self.organization.name,
            school=self.school.name,
            employee_group=self.employee_group.name,
            client_request_id=client_request_id,
        )

        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "processed")
        self.assertEqual(result["counts"]["created"], 1)
        self.assertEqual(result["counts"]["already_signed"], 1)
        self.assertEqual(result["counts"]["eligible_users"], 2)

        replay = launch_staff_policy_campaign(
            policy_version=self.policy_version.name,
            organization=self.organization.name,
            school=self.school.name,
            employee_group=self.employee_group.name,
            client_request_id=client_request_id,
        )
        self.assertTrue(replay.get("ok"))
        self.assertTrue(replay.get("idempotent"))
        self.assertEqual(replay.get("status"), "already_processed")

        dashboard = get_staff_policy_signature_dashboard(
            policy_version=self.policy_version.name,
            organization=self.organization.name,
            school=self.school.name,
            employee_group=self.employee_group.name,
        )
        summary = dashboard.get("summary") or {}
        self.assertEqual(summary.get("eligible_users"), 2)
        self.assertEqual(summary.get("signed"), 1)
        self.assertEqual(summary.get("pending"), 1)

        pending_rows = (dashboard.get("rows") or {}).get("pending") or []
        self.assertEqual(len(pending_rows), 1)
