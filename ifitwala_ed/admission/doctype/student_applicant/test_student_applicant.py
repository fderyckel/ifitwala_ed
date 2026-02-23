# ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py
# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.doctype.student_applicant.student_applicant import academic_year_intent_query


class TestStudentApplicant(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self._ensure_role("Admissions Applicant")
        self._ensure_role("Student")
        self._ensure_role("Guardian")
        self._ensure_admissions_role("Administrator", "Admission Manager")
        frappe.clear_cache(user="Administrator")
        self.staff_user = self._create_user("Admissions", "Staff", add_role="Admission Manager")
        frappe.set_user(self.staff_user.name)
        self.org = self._create_org()
        self.parent_school = self._create_school("Admissions Root", "AR", self.org, is_group=1)
        self.leaf_school = self._create_school("Admissions Leaf", "AL", self.org, parent=self.parent_school, is_group=0)

        self.visible_ay = self._create_academic_year(self.leaf_school, "2025-2026", archived=0, visible=1)
        self.archived_ay = self._create_academic_year(self.leaf_school, "2024-2025", archived=1, visible=1)
        self.hidden_ay = self._create_academic_year(self.leaf_school, "2023-2024", archived=0, visible=0)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_academic_year_query_filters_visibility(self):
        rows = academic_year_intent_query(
            "Academic Year",
            "",
            "name",
            0,
            50,
            {"school": self.leaf_school},
        )
        names = {r[0] for r in rows}
        self.assertIn(self.visible_ay, names)
        self.assertNotIn(self.archived_ay, names)
        self.assertNotIn(self.hidden_ay, names)

    def test_academic_year_query_scope_leaf_ancestor(self):
        orphan_leaf = self._create_school("Orphan Leaf", "OL", self.org, parent=self.parent_school, is_group=0)
        parent_ay = self._create_academic_year(self.parent_school, "2026-2027", archived=0, visible=1)
        rows = academic_year_intent_query(
            "Academic Year",
            "",
            "name",
            0,
            50,
            {"school": orphan_leaf},
        )
        names = {r[0] for r in rows}
        self.assertIn(parent_ay, names)

    def test_academic_year_query_scope_non_leaf_child_ancestor(self):
        intermediate_school = self._create_school(
            "Intermediate School", "IS", self.org, parent=self.parent_school, is_group=1
        )
        self._create_school("Intermediate Leaf A", "IA", self.org, parent=intermediate_school, is_group=0)
        self._create_school("Intermediate Leaf B", "IB", self.org, parent=intermediate_school, is_group=0)
        parent_ay = self._create_academic_year(self.parent_school, "2027-2028", archived=0, visible=1)

        rows = academic_year_intent_query(
            "Academic Year",
            "",
            "name",
            0,
            50,
            {"school": intermediate_school},
        )
        names = {r[0] for r in rows}
        self.assertIn(parent_ay, names)

    def test_validation_blocks_archived_ay(self):
        applicant = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Test",
                "last_name": "Applicant",
                "organization": self.org,
                "school": self.leaf_school,
                "academic_year": self.archived_ay,
                "application_status": "Draft",
            }
        )
        with self.assertRaises(frappe.ValidationError):
            applicant.insert(ignore_permissions=True)

    def test_title_autofills_from_name_parts_when_empty(self):
        applicant = self._create_student_applicant(
            first_name="Ada",
            middle_name="M.",
            last_name="Lovelace",
        )
        self.assertEqual(applicant.title, "Ada M. Lovelace")

    def test_title_is_not_overwritten_when_already_set(self):
        applicant = self._create_student_applicant(
            first_name="Grace",
            middle_name="Brewster",
            last_name="Hopper",
            title="Captain Hopper",
        )
        self.assertEqual(applicant.title, "Captain Hopper")

    def test_submitted_to_under_review_transition(self):
        applicant = self._create_student_applicant()
        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.reload()
        self.assertEqual(applicant.application_status, "Submitted")
        self.assertTrue(bool(applicant.submitted_at))

        applicant.mark_under_review()
        applicant.reload()
        self.assertEqual(applicant.application_status, "Under Review")

    def test_submit_application_allows_invited_without_manual_in_progress_step(self):
        applicant = self._create_student_applicant()
        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()

        applicant.submit_application()
        applicant.reload()

        self.assertEqual(applicant.application_status, "Submitted")
        self.assertTrue(bool(applicant.submitted_at))

    def test_submit_application_allows_missing_info_without_manual_in_progress_step(self):
        applicant = self._create_student_applicant()
        applicant.db_set("application_status", "Missing Info", update_modified=False)
        applicant.reload()

        applicant.submit_application()
        applicant.reload()

        self.assertEqual(applicant.application_status, "Submitted")
        self.assertTrue(bool(applicant.submitted_at))

    def test_reject_disables_portal_user(self):
        user = self._create_user("Applicant", "Portal", add_role="Admissions Applicant")
        applicant = self._create_student_applicant()
        applicant.flags.from_applicant_invite = True
        applicant.applicant_user = user.name
        applicant.save(ignore_permissions=True)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.reject_application("Not eligible")

        user.reload()
        self.assertEqual(user.enabled, 0)

    def test_has_required_interviews_returns_recent_items(self):
        applicant = self._create_student_applicant()
        interview = frappe.get_doc(
            {
                "doctype": "Applicant Interview",
                "student_applicant": applicant.name,
                "interview_date": frappe.utils.nowdate(),
                "interview_type": "Student",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Interview", interview.name))

        payload = applicant.has_required_interviews()
        self.assertEqual(payload.get("count"), 1)
        self.assertTrue(payload.get("ok"))
        items = payload.get("items") or []
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get("name"), interview.name)

    def test_promotion_copies_approved_applicant_document_files(self):
        doc_type = self._create_applicant_document_type(code="application_form")
        applicant = self._create_student_applicant()
        self._create_applicant_health_profile(applicant.name)

        frappe.set_user("Administrator")
        try:
            applicant_doc = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                    "review_status": "Approved",
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_doc.name))

        source_file = frappe.get_doc(
            {
                "doctype": "File",
                "attached_to_doctype": "Applicant Document",
                "attached_to_name": applicant_doc.name,
                "file_name": "supporting.txt",
                "is_private": 1,
                "content": b"promote-me",
            }
        )
        source_file.insert(ignore_permissions=True)
        self._created.append(("File", source_file.name))

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))
        applicant.reload()
        self.assertEqual(applicant.application_status, "Promoted")

        copied_files = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "Student", "attached_to_name": student_name},
            fields=["name"],
        )
        copied_file_names = [row["name"] for row in copied_files]
        self.assertTrue(copied_file_names)
        for name in copied_file_names:
            self._created.append(("File", name))

        copied_classifications = frappe.get_all(
            "File Classification",
            filters={
                "primary_subject_type": "Student",
                "primary_subject_id": student_name,
                "source_file": source_file.name,
            },
            fields=["name"],
        )
        copied_classification_names = [row["name"] for row in copied_classifications]
        self.assertTrue(copied_classification_names)
        for name in copied_classification_names:
            self._created.append(("File Classification", name))

    def test_required_document_type_from_parent_school_applies_to_child_school_applicant(self):
        code = f"parent_req_{frappe.generate_hash(length=6)}"
        doc_type = self._create_applicant_document_type(
            code=code,
            school=self.parent_school,
            is_required=1,
        )
        applicant = self._create_student_applicant()

        missing_payload = applicant.has_required_documents()
        self.assertFalse(missing_payload.get("ok"))
        self.assertIn(code, missing_payload.get("missing") or [])

        frappe.set_user("Administrator")
        try:
            applicant_doc = frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": applicant.name,
                    "document_type": doc_type,
                    "review_status": "Approved",
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.set_user(self.staff_user.name)
        self._created.append(("Applicant Document", applicant_doc.name))

        approved_payload = applicant.has_required_documents()
        self.assertTrue(approved_payload.get("ok"))
        self.assertNotIn(code, approved_payload.get("missing") or [])
        self.assertNotIn(code, approved_payload.get("unapproved") or [])

    def test_profile_information_reports_missing_required_fields(self):
        applicant = self._create_student_applicant()
        payload = applicant.has_required_profile_information()
        self.assertFalse(payload.get("ok"))
        self.assertIn("Date of Birth", payload.get("missing") or [])
        self.assertIn("First Language", payload.get("missing") or [])
        self.assertIn("Nationality", payload.get("missing") or [])

    def test_promotion_copies_profile_information_to_student(self):
        language = self._get_or_create_language_xtra()
        country = self._get_any_country()
        if not country:
            self.skipTest("Country records are required for this profile mapping test.")

        applicant = self._create_student_applicant(
            student_preferred_name="Ada",
            student_date_of_birth="2014-01-01",
            student_gender="Female",
            student_mobile_number="+14155550199",
            student_joining_date=frappe.utils.nowdate(),
            student_first_language=language,
            student_second_language=language,
            student_nationality=country,
            student_second_nationality=country,
            residency_status="Local Resident",
        )
        self._create_applicant_health_profile(applicant.name)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))
        student = frappe.get_doc("Student", student_name)
        self.assertEqual(student.student_preferred_name, "Ada")
        self.assertEqual(str(student.student_date_of_birth), "2014-01-01")
        self.assertEqual(student.student_gender, "Female")
        self.assertEqual(student.student_mobile_number, "+14155550199")
        self.assertEqual(str(student.student_joining_date), str(applicant.student_joining_date))
        self.assertEqual(student.student_first_language, language)
        self.assertEqual(student.student_second_language, language)
        self.assertEqual(student.student_nationality, country)
        self.assertEqual(student.student_second_nationality, country)
        self.assertEqual(student.residency_status, "Local Resident")
        self.assertEqual(student.anchor_school, applicant.school)

    def test_misconfigured_required_document_type_is_still_required_in_readiness(self):
        code = f"misconfigured_req_{frappe.generate_hash(length=6)}"
        doc_type = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Type {code}",
                "organization": self.org,
                "school": self.parent_school,
                "is_required": 1,
                "is_active": 0,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc_type.name))
        frappe.db.set_value("Applicant Document Type", doc_type.name, "is_active", 1, update_modified=False)

        applicant = self._create_student_applicant()
        payload = applicant.has_required_documents()
        self.assertFalse(payload.get("ok"))
        self.assertIn(code, payload.get("required") or [])
        self.assertIn(code, payload.get("missing") or [])

    def test_promotion_copies_health_profile_to_student_patient(self):
        applicant = self._create_student_applicant()
        self._create_applicant_health_profile(
            applicant.name,
            blood_group="O Positive",
            allergies=1,
            food_allergies="Peanuts",
            asthma="Mild",
            vaccinations=[
                {
                    "vaccine_name": "MMR",
                    "date": frappe.utils.nowdate(),
                    "vaccination_proof": "/files/mmr-proof.png",
                    "additional_notes": "Dose 1",
                }
            ],
        )

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        student_patient_name = frappe.db.get_value("Student Patient", {"student": student_name}, "name")
        self.assertTrue(student_patient_name)
        self._created.append(("Student Patient", student_patient_name))

        student_patient = frappe.get_doc("Student Patient", student_patient_name)
        self.assertEqual(student_patient.blood_group, "O Positive")
        self.assertEqual(int(student_patient.allergies or 0), 1)
        self.assertEqual(student_patient.food_allergies, "Peanuts")
        self.assertEqual(student_patient.asthma, "Mild")
        self.assertEqual(len(student_patient.vaccinations or []), 1)
        self.assertEqual(student_patient.vaccinations[0].vaccine_name, "MMR")
        self.assertEqual(str(student_patient.vaccinations[0].date), frappe.utils.nowdate())

    def test_upgrade_identity_requires_active_enrollment(self):
        applicant = self._create_student_applicant()
        self._create_applicant_health_profile(applicant.name)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        with self.assertRaises(frappe.ValidationError):
            applicant.upgrade_identity()

    def test_upgrade_identity_is_idempotent_and_provisions_roles(self):
        applicant_user = self._create_user("Applicant", "Portal", add_role="Admissions Applicant")
        applicant = self._create_student_applicant()
        self._create_applicant_health_profile(applicant.name)

        guardian = self._create_guardian(
            first_name="Parent",
            last_name="One",
            email=applicant_user.name,
            mobile="+14155550123",
            user=applicant_user.name,
        )
        applicant.append(
            "guardians",
            {
                "guardian": guardian.name,
                "relationship": "Mother",
                "is_primary": 1,
                "can_consent": 1,
            },
        )
        applicant.flags.from_applicant_invite = True
        applicant.flags.from_contact_sync = True
        applicant.applicant_user = applicant_user.name
        applicant.applicant_email = applicant_user.name
        applicant.portal_account_email = applicant_user.name
        applicant.save(ignore_permissions=True)

        applicant.db_set("application_status", "Invited", update_modified=False)
        applicant.reload()
        applicant.mark_in_progress()
        applicant.submit_application()
        applicant.mark_under_review()
        applicant.db_set("application_status", "Approved", update_modified=False)
        applicant.reload()

        student_name = applicant.promote_to_student()
        self._created.append(("Student", student_name))

        original_exists = frappe.db.exists

        def exists_with_enrollment(doctype, filters=None, *args, **kwargs):
            if doctype == "Program Enrollment" and isinstance(filters, dict):
                if filters.get("student") == student_name and int(filters.get("archived") or 0) == 0:
                    return "PE-MOCK-0001"
            return original_exists(doctype, filters, *args, **kwargs)

        with patch.object(frappe.db, "exists", side_effect=exists_with_enrollment):
            first = applicant.upgrade_identity()
            second = applicant.upgrade_identity()

        self.assertTrue(first.get("ok"))
        self.assertEqual(second.get("guardians_added"), 0)

        student = frappe.get_doc("Student", student_name)
        guardian_links = [row.guardian for row in (student.get("guardians") or []) if row.guardian == guardian.name]
        self.assertEqual(len(guardian_links), 1)

        user = frappe.get_doc("User", applicant_user.name)
        self.assertEqual(int(user.enabled or 0), 1)
        role_names = set(
            frappe.get_all(
                "Has Role",
                filters={"parent": applicant_user.name, "parenttype": "User"},
                pluck="role",
            )
        )
        self.assertIn("Guardian", role_names)
        self.assertIn("Student", role_names)
        self.assertNotIn("Admissions Applicant", role_names)

    def _ensure_admissions_role(self, user, role):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
            self._created.append(("Role", role))
        if not frappe.db.exists("Has Role", {"parent": user, "role": role}):
            frappe.get_doc(
                {
                    "doctype": "Has Role",
                    "parent": user,
                    "parenttype": "User",
                    "parentfield": "roles",
                    "role": role,
                }
            ).insert(ignore_permissions=True)
        frappe.clear_cache(user=user)

    def _ensure_role(self, role):
        if frappe.db.exists("Role", role):
            return
        frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
        self._created.append(("Role", role))

    def _create_org(self):
        name = f"Org-{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": name,
                "abbr": name[:6].upper(),
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(self, school_name, abbr, organization, parent=None, is_group=0):
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": school_name,
                "abbr": abbr,
                "organization": organization,
                "is_group": 1 if is_group else 0,
                "parent_school": parent,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _create_academic_year(self, school, academic_year_name, archived=0, visible=1):
        doc = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": academic_year_name,
                "school": school,
                "archived": archived,
                "visible_to_admission": visible,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Academic Year", doc.name))
        return doc.name

    def _create_student_applicant(self, **overrides):
        seed = frappe.generate_hash(length=6)
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Test",
                "last_name": f"Applicant {seed}",
                "organization": self.org,
                "school": self.leaf_school,
                "application_status": "Draft",
                **overrides,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc

    def _create_user(self, first_name, last_name, add_role=None):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"user-{frappe.generate_hash(length=8)}@example.com",
                "first_name": first_name,
                "last_name": last_name,
                "enabled": 1,
            }
        )
        if add_role:
            if not frappe.db.exists("Role", add_role):
                frappe.get_doc({"doctype": "Role", "role_name": add_role}).insert(ignore_permissions=True)
                self._created.append(("Role", add_role))
            user.append("roles", {"role": add_role})
        user.insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user

    def _create_guardian(self, *, first_name, last_name, email, mobile, user=None):
        doc = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": first_name,
                "guardian_last_name": last_name,
                "guardian_email": email,
                "guardian_mobile_phone": mobile,
                "user": user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Guardian", doc.name))
        return doc

    def _create_applicant_document_type(
        self,
        *,
        code,
        school=None,
        organization=None,
        is_required=0,
        is_active=1,
    ):
        existing = frappe.db.get_value("Applicant Document Type", {"code": code}, "name")
        if existing:
            return existing
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Type {code}",
                "organization": organization or self.org,
                "school": school or self.leaf_school,
                "is_active": is_active,
                "is_required": is_required,
                "classification_slot": f"admissions_{frappe.scrub(code)}",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name

    def _get_or_create_language_xtra(self) -> str:
        existing = frappe.get_all("Language Xtra", filters={"enabled": 1}, fields=["name"], limit=1)
        if existing:
            return existing[0]["name"]

        code = f"lng_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Language Xtra",
                "language_name": f"Language {code}",
                "language_code": code,
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Language Xtra", doc.name))
        return doc.name

    def _get_any_country(self) -> str | None:
        existing = frappe.get_all("Country", fields=["name"], limit=1, order_by="name asc")
        if not existing:
            return None
        return existing[0]["name"]

    def _create_applicant_health_profile(self, applicant_name, **overrides):
        frappe.set_user(self.staff_user.name)
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": applicant_name,
                "review_status": "Cleared",
                **overrides,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Health Profile", doc.name))
        return doc
