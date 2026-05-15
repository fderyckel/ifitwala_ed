# ifitwala_ed/admission/doctype/applicant_review_rule/test_applicant_review_rule.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.doctype.applicant_review_rule.applicant_review_rule import (
    get_permission_query_conditions,
    has_permission,
)


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

    def test_permission_query_conditions_use_school_scope_when_present(self):
        with patch(
            "ifitwala_ed.admission.doctype.applicant_review_rule.applicant_review_rule.get_admissions_file_staff_scope",
            return_value={
                "allowed": True,
                "bypass": False,
                "org_scope": {self.organization},
                "school_scope": {self.school},
            },
        ):
            condition = get_permission_query_conditions("manager@example.com")

        self.assertEqual(
            condition,
            f"`tabApplicant Review Rule`.`school` IN ({frappe.db.escape(self.school)})",
        )

    def test_permission_query_conditions_fall_back_to_org_scope(self):
        with patch(
            "ifitwala_ed.admission.doctype.applicant_review_rule.applicant_review_rule.get_admissions_file_staff_scope",
            return_value={
                "allowed": True,
                "bypass": False,
                "org_scope": {self.organization},
                "school_scope": set(),
            },
        ):
            condition = get_permission_query_conditions("manager@example.com")

        self.assertEqual(
            condition,
            f"`tabApplicant Review Rule`.`organization` IN ({frappe.db.escape(self.organization)})",
        )

    def test_permission_query_conditions_bypass_for_system_scope(self):
        with patch(
            "ifitwala_ed.admission.doctype.applicant_review_rule.applicant_review_rule.get_admissions_file_staff_scope",
            return_value={"allowed": True, "bypass": True, "org_scope": set(), "school_scope": set()},
        ):
            self.assertIsNone(get_permission_query_conditions("admin@example.com"))

    def test_has_permission_allows_scoped_manager_and_blocks_sibling(self):
        scope = {
            "allowed": True,
            "bypass": False,
            "org_scope": {self.organization},
            "school_scope": {self.school},
        }
        allowed_doc = {"organization": self.organization, "school": self.school}
        sibling_doc = {"organization": self.organization, "school": "Sibling School"}

        with (
            patch(
                "ifitwala_ed.admission.doctype.applicant_review_rule.applicant_review_rule.get_admissions_file_staff_scope",
                return_value=scope,
            ),
            patch(
                "ifitwala_ed.admission.doctype.applicant_review_rule.applicant_review_rule.frappe.get_roles",
                return_value=["Admission Manager"],
            ),
        ):
            self.assertTrue(has_permission(allowed_doc, ptype="write", user="manager@example.com"))
            self.assertFalse(has_permission(sibling_doc, ptype="read", user="manager@example.com"))

    def test_has_permission_keeps_admission_officer_read_only(self):
        scope = {
            "allowed": True,
            "bypass": False,
            "org_scope": {self.organization},
            "school_scope": {self.school},
        }
        doc = {"organization": self.organization, "school": self.school}

        with (
            patch(
                "ifitwala_ed.admission.doctype.applicant_review_rule.applicant_review_rule.get_admissions_file_staff_scope",
                return_value=scope,
            ),
            patch(
                "ifitwala_ed.admission.doctype.applicant_review_rule.applicant_review_rule.frappe.get_roles",
                return_value=["Admission Officer"],
            ),
        ):
            self.assertTrue(has_permission(doc, ptype="read", user="officer@example.com"))
            self.assertFalse(has_permission(doc, ptype="write", user="officer@example.com"))

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
