# ifitwala_ed/admission/doctype/applicant_document/test_applicant_document.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantDocument(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Admissions Applicant")
        self._ensure_role("Admission Officer")
        self._ensure_role("Admission Manager")

        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant_user = self._create_applicant_user()
        self.admission_officer_user = self._create_staff_user("Admission Officer")
        self.admission_manager_user = self._create_staff_user("Admission Manager")
        self.applicant = self._create_applicant(self.organization, self.school, self.applicant_user)
        self.document_type = self._create_document_type(self.organization, self.school)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_applicant_can_create_pending_document_without_review_permission(self):
        frappe.set_user(self.applicant_user)
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": self.applicant.name,
                "document_type": self.document_type,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", doc.name))
        self.assertEqual((doc.review_status or "").strip(), "Pending")

    def test_applicant_cannot_set_review_status_to_approved_on_create(self):
        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Applicant Document",
                    "student_applicant": self.applicant.name,
                    "document_type": self.document_type,
                    "review_status": "Approved",
                }
            ).insert(ignore_permissions=True)

    def test_admission_officer_can_review_document(self):
        doc = self._create_pending_document_as_applicant()
        frappe.set_user(self.admission_officer_user)
        doc = frappe.get_doc("Applicant Document", doc.name)
        doc.review_status = "Approved"
        doc.review_notes = "Reviewed by admission officer."
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.review_status, "Approved")
        self.assertEqual(doc.reviewed_by, self.admission_officer_user)
        self.assertIsNotNone(doc.reviewed_on)

    def test_admission_manager_can_set_promotable_after_approval(self):
        doc = self._create_pending_document_as_applicant()
        frappe.set_user(self.admission_manager_user)
        doc = frappe.get_doc("Applicant Document", doc.name)
        doc.review_status = "Approved"
        doc.is_promotable = 1
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.review_status, "Approved")
        self.assertTrue(bool(doc.is_promotable))
        self.assertEqual(doc.reviewed_by, self.admission_manager_user)

    def test_applicant_cannot_edit_review_notes(self):
        doc = self._create_pending_document_as_applicant()
        frappe.set_user(self.applicant_user)
        doc = frappe.get_doc("Applicant Document", doc.name)
        doc.review_notes = "Trying to self-review."
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _create_pending_document_as_applicant(self):
        frappe.set_user(self.applicant_user)
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": self.applicant.name,
                "document_type": self.document_type,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", doc.name))
        return doc

    def _create_organization(self) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Org {frappe.generate_hash(length=6)}",
                "abbr": f"ORG{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(self, organization: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"School {frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _create_applicant_user(self) -> str:
        email = f"applicant-doc-{frappe.generate_hash(length=8)}@example.com"
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Applicant",
                "last_name": "User",
                "enabled": 1,
                "roles": [{"role": "Admissions Applicant"}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", doc.name))
        frappe.clear_cache(user=doc.name)
        return doc.name

    def _create_staff_user(self, role: str) -> str:
        email = f"admission-doc-{frappe.generate_hash(length=8)}@example.com"
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Admission",
                "last_name": role.replace(" ", ""),
                "enabled": 1,
                "roles": [{"role": role}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", doc.name))
        frappe.clear_cache(user=doc.name)
        return doc.name

    def _create_applicant(self, organization: str, school: str, applicant_user: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Portal",
                "last_name": f"Applicant-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Invited",
                "applicant_user": applicant_user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc

    def _create_document_type(self, organization: str, school: str) -> str:
        code = f"doc_type_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Type {code}",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "classification_slot": f"admissions_{frappe.scrub(code)}",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name
