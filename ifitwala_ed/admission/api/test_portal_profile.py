# ifitwala_ed/admission/api/test_portal_profile.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.api.portal.profile import (
    get_applicant_profile_impl as get_applicant_profile,
)
from ifitwala_ed.admission.api.portal.profile import (
    update_applicant_profile_impl as update_applicant_profile,
)
from ifitwala_ed.admission.api.portal_test_helpers import (
    AdmissionsPortalScenarioMixin,
)


class TestPortalProfile(AdmissionsPortalScenarioMixin, FrappeTestCase):
    def test_update_applicant_profile_persists_values(self):
        language = self._get_or_create_language_xtra()
        country = self._get_any_country()
        if not country:
            self.skipTest("Country records are required for applicant profile update test.")

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            student_preferred_name="Portal Preferred",
            student_date_of_birth="2013-03-01",
            student_gender="Female",
            student_mobile_number="+14155551234",
            student_first_language=language,
            student_second_language=language,
            student_nationality=country,
            student_second_nationality=country,
            residency_status="Local Resident",
            address_line1="123 Admission Road",
            address_line2="Unit 4",
            city="Bangkok",
            state="Bangkok",
            postal_code="10110",
            country=country,
            previous_school_name="River Primary School",
            previous_grade_level="Grade 3",
            previous_curriculum="IB PYP",
            previous_school_city="Chiang Mai",
            previous_school_country=country,
            previous_language_of_instruction="English",
            previous_school_year_completed="2029-2030",
            previous_school_notes="Recent transfer from another province.",
            learning_support_status="Support details provided",
            learning_needs="Needs extra time for extended writing.",
            effective_supports="Visual planning and quiet drafting time.",
            existing_support_plans="Learning support plan available.",
            social_emotional_needs="Benefits from predictable transitions.",
            physical_access_needs="No physical access needs currently known.",
            family_support_priorities="Build confidence in classroom discussions.",
            student_strengths="Curious, kind, and persistent.",
            student_interests="Robotics and music.",
            student_activities="Community coding club.",
            student_achievements="Regional robotics finalist.",
            student_motivators="Hands-on projects.",
            student_relationship_notes="Warms up after a short personal check-in.",
            student_voice_notes="I like building things with friends.",
        )
        self.assertTrue(payload.get("ok"))
        self.assertTrue((payload.get("completeness") or {}).get("ok"))

        profile_payload = get_applicant_profile(student_applicant=self.applicant.name)
        profile = profile_payload.get("profile") or {}
        options = profile_payload.get("options") or {}
        self.assertEqual(profile.get("student_preferred_name"), "Portal Preferred")
        self.assertEqual(profile.get("student_nationality"), country)
        self.assertEqual(profile.get("student_first_language"), language)
        self.assertEqual(profile.get("address_line1"), "123 Admission Road")
        self.assertEqual(profile.get("city"), "Bangkok")
        self.assertEqual(profile.get("country"), country)
        self.assertEqual(profile.get("previous_school_name"), "River Primary School")
        self.assertEqual(profile.get("previous_school_country"), country)
        self.assertEqual(profile.get("learning_support_status"), "Support details provided")
        self.assertEqual(profile.get("learning_needs"), "Needs extra time for extended writing.")
        self.assertEqual(profile.get("effective_supports"), "Visual planning and quiet drafting time.")
        self.assertEqual(profile.get("existing_support_plans"), "Learning support plan available.")
        self.assertEqual(profile.get("social_emotional_needs"), "Benefits from predictable transitions.")
        self.assertEqual(profile.get("physical_access_needs"), "No physical access needs currently known.")
        self.assertEqual(profile.get("family_support_priorities"), "Build confidence in classroom discussions.")
        self.assertEqual(profile.get("student_strengths"), "Curious, kind, and persistent.")
        self.assertEqual(profile.get("student_interests"), "Robotics and music.")
        self.assertEqual(profile.get("student_activities"), "Community coding club.")
        self.assertEqual(profile.get("student_achievements"), "Regional robotics finalist.")
        self.assertEqual(profile.get("student_motivators"), "Hands-on projects.")
        self.assertEqual(profile.get("student_relationship_notes"), "Warms up after a short personal check-in.")
        self.assertEqual(profile.get("student_voice_notes"), "I like building things with friends.")
        self.assertIn("Support details provided", options.get("learning_support_statuses") or [])

    def test_update_applicant_profile_rejects_stale_expected_modified(self):
        frappe.set_user(self.applicant_user)
        initial = get_applicant_profile(student_applicant=self.applicant.name)
        initial_modified = initial.get("record_modified") or ""

        fresh = update_applicant_profile(
            student_applicant=self.applicant.name,
            expected_modified=initial_modified,
            student_preferred_name="Fresh Save",
        )
        self.assertTrue(bool(fresh.get("record_modified")))

        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                expected_modified=initial_modified,
                student_preferred_name="Stale Save",
            )

    def test_update_applicant_profile_persists_guardians_when_enabled(self):
        self._set_guardians_section_setting(1)
        guardian_email = f"guardian-{frappe.generate_hash(length=8)}@example.com"

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            guardians=[
                {
                    "relationship": "Mother",
                    "can_consent": 1,
                    "is_primary": 1,
                    "is_primary_guardian": 1,
                    "use_applicant_contact": 0,
                    "guardian_first_name": "Mina",
                    "guardian_last_name": "Portal",
                    "guardian_email": guardian_email,
                    "guardian_mobile_phone": "+14155550101",
                    "guardian_gender": "Female",
                    "guardian_image": "/private/files/guardian-mina.png",
                }
            ],
        )
        self.assertTrue(payload.get("ok"))
        self.assertTrue(bool(payload.get("guardian_section_enabled")))
        guardians = payload.get("guardians") or []
        self.assertEqual(len(guardians), 1)
        self.assertEqual((guardians[0].get("guardian_email") or "").strip(), guardian_email)
        self.assertTrue(bool(guardians[0].get("can_consent")))
        self.assertTrue(bool((guardians[0].get("contact") or "").strip()))

        self.applicant.reload()
        rows = self.applicant.get("guardians") or []
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].guardian_first_name, "Mina")
        self.assertEqual(rows[0].guardian_last_name, "Portal")
        self.assertEqual((rows[0].guardian_email or "").strip(), guardian_email)
        self.assertEqual(int(rows[0].can_consent or 0), 1)
        self.assertTrue(bool((rows[0].contact or "").strip()))

        self.assertTrue(
            bool(
                frappe.db.exists(
                    "Dynamic Link",
                    {
                        "parenttype": "Contact",
                        "parentfield": "links",
                        "parent": rows[0].contact,
                        "link_doctype": "Student Applicant",
                        "link_name": self.applicant.name,
                    },
                )
            )
        )

    def test_get_applicant_profile_exposes_applicant_contact_prefill_when_complete(self):
        self._set_guardians_section_setting(1)
        contact = self._create_applicant_contact(
            first_name="Mina",
            last_name="Portal",
            email=f"prefill-{frappe.generate_hash(length=8)}@example.com",
            phone="+14155550101",
        )
        self.applicant.db_set("applicant_contact", contact.name, update_modified=False)

        frappe.set_user(self.applicant_user)
        payload = get_applicant_profile(student_applicant=self.applicant.name)

        prefill = payload.get("applicant_contact_prefill") or {}
        self.assertTrue(bool(prefill.get("available")))
        self.assertEqual(prefill.get("contact"), contact.name)
        self.assertEqual(prefill.get("first_name"), "Mina")
        self.assertEqual(prefill.get("last_name"), "Portal")
        self.assertEqual(prefill.get("email"), contact.email_ids[0].email_id)
        self.assertEqual(prefill.get("mobile_phone"), "+14155550101")

    def test_get_applicant_profile_exposes_prefill_from_linked_inquiry_contact(self):
        self._set_guardians_section_setting(1)
        contact_email = f"inquiry-prefill-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_applicant_contact(
            first_name="Father",
            last_name="Inquiry",
            email=contact_email,
            phone="+14155550109",
        )
        inquiry = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Father",
                "last_name": "Inquiry",
                "email": contact_email,
                "phone_number": "+14155550109",
                "type_of_inquiry": "Admission",
                "organization": self.organization,
                "school": self.school,
                "contact": contact.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Inquiry", inquiry.name))
        self.applicant.db_set("inquiry", inquiry.name, update_modified=False)
        self.applicant.db_set("applicant_contact", "", update_modified=False)

        frappe.set_user(self.applicant_user)
        payload = get_applicant_profile(student_applicant=self.applicant.name)

        prefill = payload.get("applicant_contact_prefill") or {}
        self.assertTrue(bool(prefill.get("available")))
        self.assertEqual(prefill.get("contact"), contact.name)
        self.assertEqual(prefill.get("first_name"), "Father")
        self.assertEqual(prefill.get("last_name"), "Inquiry")
        self.assertEqual(prefill.get("email"), contact_email)
        self.assertEqual(prefill.get("mobile_phone"), "+14155550109")

        self.applicant.reload()
        self.assertFalse(bool((self.applicant.applicant_contact or "").strip()))

    def test_get_applicant_profile_marks_applicant_contact_prefill_unavailable_when_incomplete(self):
        self._set_guardians_section_setting(1)
        contact = self._create_applicant_contact(
            first_name="Mina",
            last_name="Portal",
            email=f"incomplete-{frappe.generate_hash(length=8)}@example.com",
            phone="",
        )
        self.applicant.db_set("applicant_contact", contact.name, update_modified=False)

        frappe.set_user(self.applicant_user)
        payload = get_applicant_profile(student_applicant=self.applicant.name)

        prefill = payload.get("applicant_contact_prefill") or {}
        self.assertFalse(bool(prefill.get("available")))
        self.assertEqual(prefill.get("contact"), contact.name)

    def test_update_applicant_profile_hydrates_guardian_from_applicant_contact_when_checked(self):
        self._set_guardians_section_setting(1)
        contact_email = f"reuse-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_applicant_contact(
            first_name="Mina",
            last_name="Portal",
            email=contact_email,
            phone="+14155550101",
        )
        self.applicant.db_set("applicant_contact", contact.name, update_modified=False)

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            guardians=[
                {
                    "relationship": "Mother",
                    "use_applicant_contact": 1,
                    "is_primary": 1,
                    "is_primary_guardian": 1,
                    "guardian_image": "/private/files/guardian-mina.png",
                }
            ],
        )

        guardians = payload.get("guardians") or []
        self.assertEqual(len(guardians), 1)
        self.assertEqual(guardians[0].get("contact"), contact.name)
        self.assertEqual(guardians[0].get("guardian_first_name"), "Mina")
        self.assertEqual(guardians[0].get("guardian_last_name"), "Portal")
        self.assertEqual(guardians[0].get("guardian_email"), contact_email)
        self.assertEqual(guardians[0].get("guardian_mobile_phone"), "+14155550101")

        self.applicant.reload()
        row = self.applicant.get("guardians")[0]
        self.assertEqual(row.contact, contact.name)
        self.assertEqual(row.guardian_first_name, "Mina")
        self.assertEqual(row.guardian_last_name, "Portal")
        self.assertEqual(row.guardian_email, contact_email)
        self.assertEqual(row.guardian_mobile_phone, "+14155550101")

    def test_update_applicant_profile_checked_applicant_contact_keeps_user_edits(self):
        self._set_guardians_section_setting(1)
        original_email = f"reuse-edit-{frappe.generate_hash(length=8)}@example.com"
        edited_email = f"reuse-edited-{frappe.generate_hash(length=8)}@example.com"
        contact = self._create_applicant_contact(
            first_name="Mina",
            last_name="Portal",
            email=original_email,
            phone="+14155550101",
        )
        self.applicant.db_set("applicant_contact", contact.name, update_modified=False)

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            guardians=[
                {
                    "relationship": "Mother",
                    "use_applicant_contact": 1,
                    "is_primary": 1,
                    "is_primary_guardian": 1,
                    "guardian_first_name": "Mina Edited",
                    "guardian_email": edited_email,
                    "guardian_mobile_phone": "+14155550102",
                    "guardian_image": "/private/files/guardian-mina.png",
                }
            ],
        )

        guardians = payload.get("guardians") or []
        self.assertEqual(guardians[0].get("guardian_first_name"), "Mina Edited")
        self.assertEqual(guardians[0].get("guardian_last_name"), "Portal")
        self.assertEqual(guardians[0].get("guardian_email"), edited_email)
        self.assertEqual(guardians[0].get("guardian_mobile_phone"), "+14155550102")

        contact.reload()
        self.assertEqual(contact.first_name, "Mina Edited")
        self.assertEqual(contact.mobile_no, "+14155550102")
        contact_emails = {row.email_id for row in contact.get("email_ids") or []}
        self.assertIn(edited_email, contact_emails)
        primary_emails = [row.email_id for row in contact.get("email_ids") or [] if int(row.is_primary or 0)]
        self.assertEqual(primary_emails, [edited_email])

    def test_update_applicant_profile_rejects_unlinked_contact_email_for_guardian(self):
        self._set_guardians_section_setting(1)
        foreign_email = f"foreign-{frappe.generate_hash(length=8)}@example.com"
        contact = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": "Foreign",
                "last_name": "Contact",
                "email_ids": [{"email_id": foreign_email, "is_primary": 1}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Contact", contact.name))

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                guardians=[
                    {
                        "relationship": "Father",
                        "guardian_first_name": "Other",
                        "guardian_last_name": "Family",
                        "guardian_email": foreign_email,
                        "guardian_mobile_phone": "+14155550102",
                        "guardian_image": "/private/files/guardian-other.png",
                    }
                ],
            )

    def test_update_applicant_profile_forces_non_primary_guardian_to_non_signing(self):
        self._set_guardians_section_setting(1)
        guardian_email = f"secondary-{frappe.generate_hash(length=8)}@example.com"

        frappe.set_user(self.applicant_user)
        payload = update_applicant_profile(
            student_applicant=self.applicant.name,
            guardians=[
                {
                    "relationship": "Aunt",
                    "can_consent": 1,
                    "is_primary": 0,
                    "is_primary_guardian": 0,
                    "use_applicant_contact": 0,
                    "guardian_first_name": "Secondary",
                    "guardian_last_name": "Guardian",
                    "guardian_email": guardian_email,
                    "guardian_mobile_phone": "+14155550109",
                    "guardian_gender": "Female",
                    "guardian_image": "/private/files/guardian-secondary.png",
                }
            ],
        )

        self.assertTrue(payload.get("ok"))
        guardians = payload.get("guardians") or []
        self.assertEqual(len(guardians), 1)
        self.assertFalse(bool(guardians[0].get("can_consent")))

        self.applicant.reload()
        rows = self.applicant.get("guardians") or []
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0].can_consent or 0), 0)

    def test_update_applicant_profile_rejects_changing_admission_date(self):
        self.applicant.db_set("student_joining_date", "2026-01-10", update_modified=False)
        self.applicant.reload()

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.PermissionError):
            update_applicant_profile(
                student_applicant=self.applicant.name,
                student_joining_date="2026-02-10",
            )
