# ifitwala_ed/api/test_focus_policy_signature.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.api.focus import (
    ACTION_POLICY_STAFF_SIGN,
    acknowledge_staff_policy,
    get_focus_context,
    list_focus_items,
)
from ifitwala_ed.api.policy_signature import launch_staff_policy_campaign
from ifitwala_ed.tests.factories.organization import make_organization
from ifitwala_ed.tests.factories.users import make_user


class TestFocusPolicySignature(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.created: list[tuple[str, str]] = []

        self.organization = make_organization(prefix="FPS Org")
        self.created.append(("Organization", self.organization.name))
        self.school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"FPS School {frappe.generate_hash(length=6)}",
                "abbr": f"FP{frappe.generate_hash(length=4)}",
                "organization": self.organization.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("School", self.school.name))

        self.employee_group = frappe.get_doc(
            {
                "doctype": "Employee Group",
                "employee_group_name": f"FPS Group {frappe.generate_hash(length=6)}",
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee Group", self.employee_group.name))

        self.staff_user = make_user()
        self.created.append(("User", self.staff_user.name))
        self.employee = self._make_employee(self.staff_user.name)

        self.policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"focus_staff_policy_{frappe.generate_hash(length=8)}",
                "policy_title": "Staff Cybersecurity",
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
                "policy_text": "<p>Security policy</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", self.policy_version.name))

        launch_staff_policy_campaign(
            policy_version=self.policy_version.name,
            organization=self.organization.name,
            school=self.school.name,
            employee_group=self.employee_group.name,
            client_request_id=f"fps-launch-{frappe.generate_hash(length=8)}",
        )

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
                "employee_first_name": "Focus",
                "employee_last_name": f"Policy-{frappe.generate_hash(length=5)}",
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

    def test_policy_signature_focus_flow(self):
        frappe.set_user(self.staff_user.name)

        items = list_focus_items(open_only=1, limit=50, offset=0)
        policy_items = [row for row in items if row.get("action_type") == ACTION_POLICY_STAFF_SIGN]
        self.assertTrue(policy_items, "Expected policy signature action in focus list")

        focus_item_id = policy_items[0]["id"]
        ctx = get_focus_context(focus_item_id=focus_item_id)
        self.assertEqual(ctx.get("reference_doctype"), "Policy Version")
        policy_ctx = ctx.get("policy_signature") or {}
        self.assertEqual(policy_ctx.get("policy_version"), self.policy_version.name)
        self.assertEqual(policy_ctx.get("employee"), self.employee.name)
        self.assertFalse(policy_ctx.get("is_acknowledged"))

        client_request_id = f"fps-ack-{frappe.generate_hash(length=8)}"
        result = acknowledge_staff_policy(
            focus_item_id=focus_item_id,
            client_request_id=client_request_id,
        )
        self.assertTrue(result.get("ok"))
        self.assertEqual(result.get("status"), "processed")
        self.assertEqual(result.get("employee"), self.employee.name)
        self.assertGreaterEqual(result.get("closed_todos") or 0, 1)

        ack_exists = frappe.db.exists(
            "Policy Acknowledgement",
            {
                "policy_version": self.policy_version.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee.name,
            },
        )
        self.assertTrue(ack_exists)

        replay = acknowledge_staff_policy(
            focus_item_id=focus_item_id,
            client_request_id=client_request_id,
        )
        self.assertTrue(replay.get("ok"))
        self.assertTrue(replay.get("idempotent"))
        self.assertEqual(replay.get("status"), "already_processed")
