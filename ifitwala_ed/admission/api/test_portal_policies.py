# ifitwala_ed/admission/api/test_portal_policies.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.api.portal.policies import (
    acknowledge_policy_impl as acknowledge_policy,
)
from ifitwala_ed.admission.api.portal.policies import (
    get_applicant_policies_impl as get_applicant_policies,
)
from ifitwala_ed.admission.api.portal_test_helpers import (
    AdmissionsPortalScenarioMixin,
    _admission_settings_has_field,
    _policy_schema_available,
)
from ifitwala_ed.governance.policy_utils import institutional_policy_db_has_column


class TestPortalPolicies(AdmissionsPortalScenarioMixin, FrappeTestCase):
    def test_get_applicant_policies_includes_expected_signature_name(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")
        frappe.set_user(self.applicant_user)
        payload = get_applicant_policies(student_applicant=self.applicant.name)
        policies = payload.get("policies") or []
        self.assertTrue(bool(policies))

        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()
        target = next(
            (row for row in policies if row.get("policy_version") == self.policy_version),
            None,
        )
        self.assertTrue(bool(target))
        self.assertEqual(target.get("expected_signature_name"), expected_name)

    def test_get_applicant_policies_includes_acknowledgement_clauses(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")

        version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            acknowledgement_clauses=[
                {"clause_text": "I confirm the information is accurate.", "is_required": 1},
                {"clause_text": "I agree to optional reminders.", "is_required": 0},
            ],
        )

        frappe.set_user(self.applicant_user)
        payload = get_applicant_policies(student_applicant=self.applicant.name)
        target = next((row for row in (payload.get("policies") or []) if row.get("policy_version") == version), None)

        self.assertTrue(bool(target))
        clauses = target.get("acknowledgement_clauses") or []
        self.assertEqual(len(clauses), 2)
        self.assertEqual(clauses[0].get("clause_text"), "I confirm the information is accurate.")
        self.assertTrue(bool(clauses[0].get("is_required")))

    def test_get_applicant_policies_sanitizes_policy_html(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")

        version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            policy_text='<h1>Applicant Policy</h1><p>Allowed</p><script>alert(1)</script><img src="x" onerror="alert(2)">',
        )

        frappe.set_user(self.applicant_user)
        payload = get_applicant_policies(student_applicant=self.applicant.name)
        target = next((row for row in (payload.get("policies") or []) if row.get("policy_version") == version), None)

        self.assertTrue(bool(target))
        self.assertIn("<h2>Applicant Policy</h2>", target.get("content_html") or "")
        self.assertIn("<p>Allowed</p>", target.get("content_html") or "")
        self.assertNotIn("<script", target.get("content_html") or "")
        self.assertNotIn("onerror", target.get("content_html") or "")

    def test_acknowledge_policy_requires_attestation_confirmation(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")
        frappe.set_user(self.applicant_user)
        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()

        with self.assertRaises(frappe.ValidationError):
            acknowledge_policy(
                student_applicant=self.applicant.name,
                policy_version=self.policy_version,
                typed_signature_name=expected_name,
                attestation_confirmed=0,
            )

    def test_acknowledge_policy_requires_matching_typed_signature(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")
        frappe.set_user(self.applicant_user)

        with self.assertRaises(frappe.ValidationError):
            acknowledge_policy(
                student_applicant=self.applicant.name,
                policy_version=self.policy_version,
                typed_signature_name="Wrong Name",
                attestation_confirmed=1,
            )

    def test_acknowledge_policy_requires_required_clauses(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")

        version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            acknowledgement_clauses=[
                {"clause_text": "I confirm the information is accurate.", "is_required": 1},
            ],
        )
        frappe.set_user(self.applicant_user)
        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()

        with self.assertRaises(frappe.ValidationError):
            acknowledge_policy(
                student_applicant=self.applicant.name,
                policy_version=version,
                typed_signature_name=expected_name,
                attestation_confirmed=1,
                checked_clause_names=[],
            )

    def test_acknowledge_policy_creates_row_for_valid_signature(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for applicant policy tests.")
        frappe.set_user(self.applicant_user)
        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()

        payload = acknowledge_policy(
            student_applicant=self.applicant.name,
            policy_version=self.policy_version,
            typed_signature_name=expected_name,
            attestation_confirmed=1,
        )
        self.assertTrue(payload.get("ok"))
        self.assertTrue(bool(payload.get("acknowledged_at")))

        ack = frappe.db.get_value(
            "Policy Acknowledgement",
            {
                "policy_version": self.policy_version,
                "acknowledged_for": "Applicant",
                "context_doctype": "Student Applicant",
                "context_name": self.applicant.name,
            },
            ["name", "acknowledged_by"],
            as_dict=True,
        )
        self.assertTrue(bool(ack))
        self.assertEqual(ack.get("acknowledged_by"), self.applicant_user)
        self._created.append(("Policy Acknowledgement", ack.get("name")))

    def test_acknowledge_policy_family_mode_creates_guardian_context(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for family acknowledgement tests.")
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")
        if not institutional_policy_db_has_column("admissions_acknowledgement_mode"):
            self.skipTest(
                "Institutional Policy.admissions_acknowledgement_mode is required for family acknowledgement tests."
            )

        self._set_admissions_access_mode("Family Workspace")
        family_user = self._create_family_user()
        guardian = self._create_guardian_record(user=family_user.name, is_primary_guardian=True)
        self._link_family_guardian(self.applicant, guardian_name=guardian.name, user=family_user.name)
        family_policy_version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            admissions_acknowledgement_mode="Family Acknowledgement",
        )

        frappe.set_user(family_user.name)
        policies = get_applicant_policies(student_applicant=self.applicant.name)
        target = next(
            (
                row
                for row in (policies.get("policies") or [])
                if (row.get("policy_version") or "").strip() == family_policy_version
            ),
            None,
        )
        self.assertTrue(bool(target))

        payload = acknowledge_policy(
            student_applicant=self.applicant.name,
            policy_version=family_policy_version,
            typed_signature_name=target.get("expected_signature_name"),
            attestation_confirmed=1,
        )
        self.assertTrue(payload.get("ok"))

        ack = frappe.db.get_value(
            "Policy Acknowledgement",
            {
                "policy_version": family_policy_version,
                "acknowledged_for": "Guardian",
                "context_doctype": "Guardian",
                "context_name": guardian.name,
            },
            ["name", "acknowledged_by"],
            as_dict=True,
        )
        self.assertTrue(bool(ack))
        self._created.append(("Policy Acknowledgement", ack.get("name")))
        self.assertEqual((ack.get("acknowledged_by") or "").strip(), family_user.name)

    def test_family_mode_policy_is_actionably_blocked_for_single_applicant_user(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for family acknowledgement tests.")
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")
        if not institutional_policy_db_has_column("admissions_acknowledgement_mode"):
            self.skipTest(
                "Institutional Policy.admissions_acknowledgement_mode is required for family acknowledgement tests."
            )

        self._set_admissions_access_mode("Single Applicant Workspace")
        family_policy_version = self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            admissions_acknowledgement_mode="Family Acknowledgement",
        )

        frappe.set_user(self.applicant_user)
        policies = get_applicant_policies(student_applicant=self.applicant.name)
        target = next(
            (
                row
                for row in (policies.get("policies") or [])
                if (row.get("policy_version") or "").strip() == family_policy_version
            ),
            None,
        )
        self.assertTrue(bool(target))
        self.assertFalse(bool(target.get("can_acknowledge")))
        self.assertIn("single-applicant mode", target.get("blocked_reason") or "")
        self.assertNotIn("Guardian Portal", target.get("blocked_reason") or "")

        expected_name = f"{self.applicant.first_name} {self.applicant.last_name}".strip()
        with self.assertRaises(frappe.PermissionError) as exc:
            acknowledge_policy(
                student_applicant=self.applicant.name,
                policy_version=family_policy_version,
                typed_signature_name=expected_name,
                attestation_confirmed=1,
            )
        self.assertIn("single-applicant mode", str(exc.exception))

    def test_acknowledge_policy_family_mode_rejects_non_primary_guardian(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for family acknowledgement tests.")
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")
        if not institutional_policy_db_has_column("admissions_acknowledgement_mode"):
            self.skipTest(
                "Institutional Policy.admissions_acknowledgement_mode is required for family acknowledgement tests."
            )

        self._set_admissions_access_mode("Family Workspace")
        family_user = self._create_family_user()
        guardian = self._create_guardian_record(user=family_user.name, is_primary_guardian=False)
        self._link_family_guardian(
            self.applicant,
            guardian_name=guardian.name,
            user=family_user.name,
            is_primary_guardian=False,
        )
        self._create_required_applicant_policy_version(
            organization=self.organization,
            school=self.school,
            admissions_acknowledgement_mode="Family Acknowledgement",
        )

        frappe.set_user(family_user.name)
        with self.assertRaises(frappe.PermissionError):
            get_applicant_policies(student_applicant=self.applicant.name)
