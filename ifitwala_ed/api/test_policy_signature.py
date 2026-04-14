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

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self.created.append(("Role", role.name))

    def _assign_role(self, user: str, role_name: str):
        self._ensure_role(role_name)
        if frappe.db.exists("Has Role", {"parent": user, "parenttype": "User", "role": role_name}):
            return
        user_doc = frappe.get_doc("User", user)
        user_doc.append("roles", {"role": role_name})
        user_doc.save(ignore_permissions=True)
        frappe.clear_cache(user=user)

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

    def _make_guardian(self, *, user: str):
        seed = frappe.generate_hash(length=6)
        phone_suffix = "".join(str(ord(ch) % 10) for ch in seed[:6])
        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": "Guardian",
                "guardian_last_name": seed,
                "guardian_email": user,
                "guardian_mobile_phone": f"+1415{phone_suffix}",
                "user": user,
                "organization": self.organization.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Guardian", guardian.name))
        return guardian

    def _make_student(self, *, user: str, guardian_name: str):
        seed = frappe.generate_hash(length=6)
        previous_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            student = frappe.get_doc(
                {
                    "doctype": "Student",
                    "student_first_name": "Policy",
                    "student_last_name": f"Student-{seed}",
                    "student_email": user,
                    "anchor_school": self.school.name,
                    "allow_direct_creation": 1,
                }
            )
            student.append(
                "guardians",
                {
                    "guardian": guardian_name,
                    "relation": "Mother",
                    "can_consent": 1,
                },
            )
            student.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = previous_import

        self.created.append(("Student", student.name))
        return student

    def test_campaign_options_load_for_hr_manager_scope(self):
        self._assign_role(self.user_one.name, "HR Manager")

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

    def test_campaign_options_scope_school_and_policy_versions_by_selected_context(self):
        sibling_school = make_school(self.organization.name, prefix="PS Sibling School")
        self.created.append(("School", sibling_school.name))

        other_organization = make_organization(prefix="PS Other Org")
        self.created.append(("Organization", other_organization.name))
        other_school = make_school(other_organization.name, prefix="PS Other School")
        self.created.append(("School", other_school.name))

        current_school_policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"staff_school_{frappe.generate_hash(length=8)}",
                "policy_title": "Current School Safeguarding",
                "policy_category": "Employment",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": self.organization.name,
                "school": self.school.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", current_school_policy.name))
        current_school_version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": current_school_policy.name,
                "version_label": "v1",
                "policy_text": "<p>Current school policy.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", current_school_version.name))

        sibling_school_policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"staff_sibling_{frappe.generate_hash(length=8)}",
                "policy_title": "Sibling School Safeguarding",
                "policy_category": "Employment",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": self.organization.name,
                "school": sibling_school.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", sibling_school_policy.name))
        sibling_school_version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": sibling_school_policy.name,
                "version_label": "v1",
                "policy_text": "<p>Sibling school policy.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", sibling_school_version.name))

        other_org_policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"staff_other_{frappe.generate_hash(length=8)}",
                "policy_title": "Other Organization Handbook",
                "policy_category": "Employment",
                "applies_to": [{"policy_audience": "Staff"}],
                "organization": other_organization.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", other_org_policy.name))
        other_org_version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": other_org_policy.name,
                "version_label": "v1",
                "policy_text": "<p>Other org policy.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", other_org_version.name))

        frappe.set_user("Administrator")
        org_payload = get_staff_policy_campaign_options(organization=self.organization.name)
        org_options = org_payload.get("options") or {}
        org_schools = org_options.get("schools") or []
        org_policy_versions = [row.get("policy_version") for row in org_options.get("policies") or []]

        self.assertIn(self.school.name, org_schools)
        self.assertIn(sibling_school.name, org_schools)
        self.assertNotIn(other_school.name, org_schools)
        self.assertIn(self.policy_version.name, org_policy_versions)
        self.assertNotIn(current_school_version.name, org_policy_versions)
        self.assertNotIn(sibling_school_version.name, org_policy_versions)
        self.assertNotIn(other_org_version.name, org_policy_versions)

        school_payload = get_staff_policy_campaign_options(
            organization=self.organization.name,
            school=self.school.name,
        )
        school_policy_versions = [
            row.get("policy_version") for row in (school_payload.get("options") or {}).get("policies") or []
        ]

        self.assertIn(self.policy_version.name, school_policy_versions)
        self.assertIn(current_school_version.name, school_policy_versions)
        self.assertNotIn(sibling_school_version.name, school_policy_versions)
        self.assertNotIn(other_org_version.name, school_policy_versions)

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

    def test_dashboard_and_campaign_preview_include_guardian_and_student_audiences(self):
        guardian_user_one = make_user(roles=["Guardian"])
        guardian_user_two = make_user(roles=["Guardian"])
        student_user_one = make_user(roles=["Student"])
        student_user_two = make_user(roles=["Student"])
        self.created.extend(
            [
                ("User", guardian_user_one.name),
                ("User", guardian_user_two.name),
                ("User", student_user_one.name),
                ("User", student_user_two.name),
            ]
        )

        guardian_one = self._make_guardian(user=guardian_user_one.name)
        guardian_two = self._make_guardian(user=guardian_user_two.name)
        student_one = self._make_student(user=student_user_one.name, guardian_name=guardian_one.name)
        self._make_student(user=student_user_two.name, guardian_name=guardian_two.name)

        mixed_policy = frappe.get_doc(
            {
                "doctype": "Institutional Policy",
                "policy_key": f"family_policy_{frappe.generate_hash(length=8)}",
                "policy_title": "Community Handbook",
                "policy_category": "Handbooks",
                "applies_to": [
                    {"policy_audience": "Staff"},
                    {"policy_audience": "Guardian"},
                    {"policy_audience": "Student"},
                ],
                "organization": self.organization.name,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Institutional Policy", mixed_policy.name))

        mixed_version = frappe.get_doc(
            {
                "doctype": "Policy Version",
                "institutional_policy": mixed_policy.name,
                "version_label": "v1",
                "policy_text": "<p>Community handbook text.</p>",
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Version", mixed_version.name))

        frappe.set_user(self.user_one.name)
        staff_ack = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": mixed_version.name,
                "acknowledged_by": self.user_one.name,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": self.employee_one.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Acknowledgement", staff_ack.name))

        frappe.set_user(guardian_user_one.name)
        guardian_ack = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": mixed_version.name,
                "acknowledged_by": guardian_user_one.name,
                "acknowledged_for": "Guardian",
                "context_doctype": "Guardian",
                "context_name": guardian_one.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Acknowledgement", guardian_ack.name))

        frappe.set_user(student_user_one.name)
        student_ack = frappe.get_doc(
            {
                "doctype": "Policy Acknowledgement",
                "policy_version": mixed_version.name,
                "acknowledged_by": student_user_one.name,
                "acknowledged_for": "Student",
                "context_doctype": "Student",
                "context_name": student_one.name,
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Policy Acknowledgement", student_ack.name))

        frappe.set_user("Administrator")
        preview = get_staff_policy_campaign_options(
            organization=self.organization.name,
            school=self.school.name,
            employee_group=self.employee_group.name,
            policy_version=mixed_version.name,
        )
        preview_rows = (preview.get("preview") or {}).get("audience_previews") or []
        preview_by_audience = {row.get("audience"): row for row in preview_rows}

        self.assertEqual((preview.get("preview") or {}).get("policy_audiences"), ["Staff", "Guardian", "Student"])
        self.assertEqual((preview.get("preview") or {}).get("to_create"), 1)
        self.assertEqual(preview_by_audience.get("Guardian", {}).get("pending"), 1)
        self.assertEqual(preview_by_audience.get("Student", {}).get("signed"), 1)
        self.assertFalse(preview_by_audience.get("Guardian", {}).get("supports_campaign_launch"))

        dashboard = get_staff_policy_signature_dashboard(
            policy_version=mixed_version.name,
            organization=self.organization.name,
            school=self.school.name,
            employee_group=self.employee_group.name,
        )
        self.assertEqual((dashboard.get("summary") or {}).get("applies_to_tokens"), ["Staff", "Guardian", "Student"])
        self.assertEqual((dashboard.get("summary") or {}).get("eligible_targets"), 6)
        self.assertEqual((dashboard.get("summary") or {}).get("signed"), 3)
        self.assertEqual((dashboard.get("summary") or {}).get("pending"), 3)

        audience_sections = dashboard.get("audiences") or []
        audience_by_name = {row.get("audience"): row for row in audience_sections}

        staff_section = audience_by_name.get("Staff") or {}
        guardian_section = audience_by_name.get("Guardian") or {}
        student_section = audience_by_name.get("Student") or {}

        self.assertEqual((staff_section.get("summary") or {}).get("to_create"), 1)
        self.assertEqual((guardian_section.get("summary") or {}).get("signed"), 1)
        self.assertEqual((guardian_section.get("summary") or {}).get("pending"), 1)
        self.assertEqual((student_section.get("summary") or {}).get("signed"), 1)
        self.assertEqual((student_section.get("summary") or {}).get("pending"), 1)

        guardian_pending_rows = (guardian_section.get("rows") or {}).get("pending") or []
        student_signed_rows = (student_section.get("rows") or {}).get("signed") or []
        self.assertEqual(len(guardian_pending_rows), 1)
        self.assertEqual(guardian_pending_rows[0].get("subject_name"), guardian_two.guardian_full_name)
        self.assertEqual(len(student_signed_rows), 1)
        self.assertEqual(student_signed_rows[0].get("record_id"), student_one.name)
