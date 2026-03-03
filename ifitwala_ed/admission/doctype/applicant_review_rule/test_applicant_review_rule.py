# ifitwala_ed/admission/doctype/applicant_review_rule/test_applicant_review_rule.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantReviewRule(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self.organization = self._create_organization("Test Org")
        self.school = self._create_school(self.organization, "Test School")

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_scope_coherence_organization_mismatch(self):
        other_org = self._create_organization("Other Org")
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Rule",
                    "organization": other_org,
                    "school": self.school,
                    "target_type": "Student Applicant",
                    "reviewers": [{"reviewer_mode": "Role Only", "reviewer_role": "Admission Manager"}],
                }
            )
            doc.insert(ignore_permissions=True)

    def test_target_fields_document_type(self):
        # Application target type cannot have document type
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Rule",
                    "organization": self.organization,
                    "school": self.school,
                    "target_type": "Student Applicant",
                    "document_type": "some_doc_type",
                    "reviewers": [{"reviewer_mode": "Role Only", "reviewer_role": "Admission Manager"}],
                }
            )
            doc.insert(ignore_permissions=True)

    def test_reviewers_role_only_missing_role(self):
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Rule",
                    "organization": self.organization,
                    "school": self.school,
                    "target_type": "Student Applicant",
                    "reviewers": [{"reviewer_mode": "Role Only", "reviewer_role": ""}],
                }
            )
            doc.insert(ignore_permissions=True)

    def test_reviewers_specific_user_missing_user(self):
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Rule",
                    "organization": self.organization,
                    "school": self.school,
                    "target_type": "Student Applicant",
                    "reviewers": [{"reviewer_mode": "Specific User", "reviewer_user": ""}],
                }
            )
            doc.insert(ignore_permissions=True)

    def test_reviewer_user_must_have_role(self):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"test_role-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Test",
                "enabled": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))

        # User lacks Admission Manager role
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Rule",
                    "organization": self.organization,
                    "school": self.school,
                    "target_type": "Student Applicant",
                    "reviewers": [
                        {
                            "reviewer_mode": "Specific User",
                            "reviewer_user": user.name,
                            "reviewer_role": "Admission Manager",
                        }
                    ],
                }
            )
            doc.insert(ignore_permissions=True)

    def test_duplicate_reviewer_rows(self):
        # Two rows with same role only
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Review Rule",
                    "organization": self.organization,
                    "school": self.school,
                    "target_type": "Student Applicant",
                    "reviewers": [
                        {"reviewer_mode": "Role Only", "reviewer_role": "Admission Manager"},
                        {"reviewer_mode": "Role Only", "reviewer_role": "Admission Manager"},
                    ],
                }
            )
            doc.insert(ignore_permissions=True)

    def _create_organization(self, name: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{name} {frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(self, organization: str, name: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{name} {frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name
