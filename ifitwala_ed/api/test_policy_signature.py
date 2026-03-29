# ifitwala_ed/api/test_policy_signature.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.api.policy_signature import (
    get_staff_policy_campaign_options,
    get_staff_policy_library,
    get_staff_policy_signature_dashboard,
    launch_staff_policy_campaign,
)
from ifitwala_ed.governance.policy_utils import ensure_policy_audience_records
from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.tests.factories.users import make_user


class TestPolicySignature(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        ensure_policy_audience_records()
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

        self.user_one = make_user(roles=["Employee"])
        self.user_two = make_user(roles=["Employee"])
        self.created.extend([("User", self.user_one.name), ("User", self.user_two.name)])

        self.employee_one = self._make_employee(self.user_one.name)
        self.employee_two = self._make_employee(self.user_two.name)

        self.policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"staff_policy_{frappe.generate_hash(length=8)}",
                "policy_title": "Staff Data Handling",
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
            self._delete_created_doc(doctype, name)
        super().tearDown()

    def _delete_created_doc(self, doctype: str, name: str):
        if not frappe.db.exists(doctype, name):
            return
        if doctype == "Policy Acknowledgement":
            frappe.db.delete("Policy Acknowledgement", {"name": name})
            return
        frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def _make_employee(self, user: str, school: str | None = None):
        school_name = (school or self.school.name).strip()
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
                "school": school_name,
                "employee_group": self.employee_group.name,
                "user_id": user,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Employee", employee.name))
        return employee

    def test_campaign_options_load_for_hr_manager_scope(self):
        frappe.add_roles(self.user_one.name, "HR Manager")

        frappe.set_user(self.user_one.name)
        payload = get_staff_policy_campaign_options(
            organization=self.organization.name,
            school=self.school.name,
            policy_version=self.policy_version.name,
        )

        options = payload.get("options") or {}
        organizations = options.get("organizations") or []
        policies = options.get("policies") or []

        self.assertIn(self.organization.name, organizations)
        self.assertTrue(any(row.get("policy_version") == self.policy_version.name for row in policies))

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

    def test_staff_policy_library_informational_signed_and_new_version_states(self):
        informational_policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"staff_info_{frappe.generate_hash(length=8)}",
                "policy_title": "Staff Handbook Overview",
                "policy_category": "Handbooks",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": self.organization.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", informational_policy.name))

        informational_version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": informational_policy.name,
                "version_label": "v1",
                "policy_text": "<p>Read this informational handbook section.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", informational_version.name))

        frappe.set_user(self.user_one.name)
        payload = get_staff_policy_library(
            organization=self.organization.name,
            school=self.school.name,
            employee_group=self.employee_group.name,
        )
        rows = payload.get("rows") or []
        by_policy = {row.get("institutional_policy"): row for row in rows}

        signed_row = by_policy.get(self.policy.name) or {}
        self.assertTrue(signed_row.get("signature_required"))
        self.assertEqual(signed_row.get("acknowledgement_status"), "signed")

        informational_row = by_policy.get(informational_policy.name) or {}
        self.assertFalse(informational_row.get("signature_required"))
        self.assertEqual(informational_row.get("acknowledgement_status"), "informational")

        frappe.set_user("Administrator")
        amendment = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": self.policy.name,
                "version_label": "v3",
                "based_on_version": self.policy_version.name,
                "change_summary": "Raised incident escalation requirement timeline.",
                "policy_text": "<p>Read and sign this policy update.</p>",
                "is_active": 1,
            }
        )
        self.policy_version.is_active = 0
        self.policy_version.save(ignore_permissions=True)
        amendment = amendment.insert(ignore_permissions=True)
        self.created.append(("Policy Version", amendment.name))

        frappe.set_user(self.user_one.name)
        updated_payload = get_staff_policy_library(
            organization=self.organization.name,
            school=self.school.name,
            employee_group=self.employee_group.name,
        )
        updated_rows = updated_payload.get("rows") or []
        updated_by_policy = {row.get("institutional_policy"): row for row in updated_rows}
        new_version_row = updated_by_policy.get(self.policy.name) or {}
        self.assertTrue(new_version_row.get("signature_required"))
        self.assertEqual(new_version_row.get("policy_version"), amendment.name)
        self.assertEqual(new_version_row.get("acknowledgement_status"), "new_version")

    def test_staff_policy_library_defaults_to_employee_school_and_inherits_parent_school_policy(self):
        parent_school = make_school(self.organization.name, prefix="PS Parent School", is_group=1)
        self.created.append(("School", parent_school.name))

        child_school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"PS Child School {frappe.generate_hash(length=6)}",
                "abbr": f"PC{frappe.generate_hash(length=3)}",
                "organization": self.organization.name,
                "parent_school": parent_school.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("School", child_school.name))

        child_user = make_user(roles=["Employee"])
        self.created.append(("User", child_user.name))
        self._make_employee(child_user.name, school=child_school.name)

        parent_school_policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"staff_parent_scope_{frappe.generate_hash(length=8)}",
                "policy_title": "Parent School Staff Policy",
                "policy_category": "Employment",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": self.organization.name,
                "school": parent_school.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", parent_school_policy.name))

        parent_school_version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": parent_school_policy.name,
                "version_label": "v1",
                "policy_text": "<p>Parent school policy text.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", parent_school_version.name))

        frappe.set_user(child_user.name)
        payload = get_staff_policy_library(organization=self.organization.name, school="")

        self.assertEqual((payload.get("filters") or {}).get("school"), child_school.name)
        rows = payload.get("rows") or []
        by_policy = {row.get("institutional_policy"): row for row in rows}
        inherited_row = by_policy.get(parent_school_policy.name) or {}
        self.assertEqual(inherited_row.get("policy_version"), parent_school_version.name)
        self.assertEqual(inherited_row.get("policy_school"), parent_school.name)
