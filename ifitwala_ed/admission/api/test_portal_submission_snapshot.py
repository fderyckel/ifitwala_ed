# ifitwala_ed/admission/api/test_portal_submission_snapshot.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.api.portal.profile import (
    get_applicant_profile_impl as get_applicant_profile,
)
from ifitwala_ed.admission.api.portal.session import get_admissions_session_impl as get_admissions_session
from ifitwala_ed.admission.api.portal.snapshot import get_applicant_snapshot_impl as get_applicant_snapshot
from ifitwala_ed.admission.api.portal.submission import submit_application_impl as submit_application
from ifitwala_ed.admission.api.portal_test_helpers import (
    AdmissionsPortalScenarioMixin,
    _admission_settings_has_field,
    _policy_schema_available,
)


class TestPortalSubmissionSnapshot(AdmissionsPortalScenarioMixin, FrappeTestCase):
    def test_submit_application_accepts_invited_state(self):
        frappe.set_user(self.applicant_user)
        payload = submit_application(student_applicant=self.applicant.name)
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("changed"))

        self.applicant.reload()
        self.assertEqual(self.applicant.application_status, "Submitted")
        self.assertTrue(bool(self.applicant.submitted_at))

    def test_submit_application_accepts_missing_info_state(self):
        self.applicant.db_set("application_status", "Missing Info", update_modified=False)
        self.applicant.reload()

        frappe.set_user(self.applicant_user)
        payload = submit_application(student_applicant=self.applicant.name)
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("changed"))

        self.applicant.reload()
        self.assertEqual(self.applicant.application_status, "Submitted")
        self.assertTrue(bool(self.applicant.submitted_at))

    def test_get_applicant_snapshot_includes_profile_and_application_context(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for readiness snapshot tests.")
        frappe.set_user(self.applicant_user)
        payload = get_applicant_snapshot(student_applicant=self.applicant.name)
        self.assertIn("profile", payload)
        self.assertIn("application_context", payload)
        self.assertIn("profile", payload.get("completeness") or {})
        self.assertIn("recommendations", payload.get("completeness") or {})
        self.assertIn("recommendations_summary", payload)

    def test_applicant_profile_rejects_other_applicant_contact_data(self):
        self._set_guardians_section_setting(1)
        other_user = self._create_applicant_user()
        other_applicant = self._create_applicant(self.organization, self.school, other_user)
        other_contact = self._create_applicant_contact(
            first_name="Other",
            last_name="Contact",
            email=f"other-contact-{frappe.generate_hash(length=8)}@example.com",
            phone="+14155550128",
        )
        other_applicant.db_set("applicant_contact", other_contact.name, update_modified=False)
        other_applicant.append(
            "guardians",
            {
                "relationship": "Mother",
                "can_consent": 1,
                "is_primary": 1,
                "is_primary_guardian": 1,
                "guardian_first_name": "Other",
                "guardian_last_name": "Guardian",
                "guardian_email": f"other-guardian-{frappe.generate_hash(length=8)}@example.com",
                "guardian_mobile_phone": "+14155550129",
                "guardian_image": "/private/files/other-guardian.png",
            },
        )
        other_applicant.save(ignore_permissions=True)

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.PermissionError):
            get_applicant_profile(student_applicant=other_applicant.name)

    def test_offer_sent_snapshot_surfaces_offer_response_action(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for admissions offer snapshot tests.")
        self._create_offer_plan(status="Offer Sent", offer_message="Review your place.")

        frappe.set_user(self.applicant_user)
        session_payload = get_admissions_session()
        snapshot = get_applicant_snapshot(student_applicant=self.applicant.name)

        self.assertEqual((session_payload.get("applicant") or {}).get("portal_status"), "Offer Sent")
        self.assertEqual((snapshot.get("enrollment_offer") or {}).get("status"), "Offer Sent")
        self.assertTrue(bool((snapshot.get("enrollment_offer") or {}).get("can_accept")))
        self.assertTrue(bool((snapshot.get("enrollment_offer") or {}).get("can_decline")))
        self.assertEqual((snapshot.get("next_actions") or [])[0].get("route_name"), "admissions-status")
        self.assertTrue(bool((snapshot.get("next_actions") or [])[0].get("is_blocking")))

    def test_offer_sent_snapshot_surfaces_course_choice_action_when_choices_are_incomplete(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for admissions offer snapshot tests.")
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        self._create_offer_plan(
            status="Offer Sent",
            optional_course_basket_groups=[humanities_group],
            enrollment_rules=[{"rule_type": "REQUIRE_GROUP_COVERAGE", "basket_group": humanities_group}],
        )

        frappe.set_user(self.applicant_user)
        snapshot = get_applicant_snapshot(student_applicant=self.applicant.name)

        actions = snapshot.get("next_actions") or []
        self.assertEqual(actions[0].get("route_name"), "admissions-course-choices")
        self.assertEqual(actions[1].get("route_name"), "admissions-status")
        self.assertFalse(bool((snapshot.get("enrollment_offer") or {}).get("course_choices_ready")))

    def test_get_admissions_session_family_workspace_returns_all_linked_applicants(self):
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")

        self._set_admissions_access_mode("Family Workspace")
        family_user = self._create_family_user()
        guardian = self._create_guardian_record(user=family_user.name, is_primary_guardian=True)
        second_applicant = self._create_applicant(self.organization, self.school, self._create_applicant_user())

        self._link_family_guardian(self.applicant, guardian_name=guardian.name, user=family_user.name)
        self._link_family_guardian(second_applicant, guardian_name=guardian.name, user=family_user.name)

        frappe.set_user(family_user.name)
        payload = get_admissions_session(student_applicant=second_applicant.name)

        self.assertEqual(payload.get("access_mode"), "Family Workspace")
        self.assertTrue(bool(payload.get("family_workspace_enabled")))
        self.assertEqual(payload.get("selected_applicant"), second_applicant.name)
        self.assertEqual((payload.get("applicant") or {}).get("name"), second_applicant.name)
        self.assertEqual(set((payload.get("user") or {}).get("roles") or []), {"Admissions Family"})
        self.assertEqual(
            {row.get("name") for row in (payload.get("available_applicants") or [])},
            {self.applicant.name, second_applicant.name},
        )
