# ifitwala_ed/admission/doctype/recommendation_submission/test_recommendation_submission.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRecommendationSubmission(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self.organization = self._create_organization("Org-RecSub")
        self.school = self._create_school(self.organization, "School-RecSub")
        self.doc_type = self._create_document_type(self.organization, self.school)
        self.template = self._create_template(self.organization, self.school, self.doc_type)
        self.applicant = self._create_applicant(self.organization, self.school)
        self.request = self._create_request(self.applicant.name, self.template)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_submission_links_validation(self):
        # Student missing/mismatch
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Submission",
                    "recommendation_request": self.request.name,
                    "student_applicant": "Wrong Applicant",
                    "recommendation_template": self.template,
                    "recommender_name": "Test Recommender",
                    "recommender_email": "recommender@example.com",
                    "answers_json": "{}",
                }
            )
            doc.insert(ignore_permissions=True)

        # Recommender mismatch
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Submission",
                    "recommendation_request": self.request.name,
                    "student_applicant": self.applicant.name,
                    "recommendation_template": self.template,
                    "recommender_name": "Wrong Name",
                    "recommender_email": "recommender@example.com",
                    "answers_json": "{}",
                }
            )
            doc.insert(ignore_permissions=True)

    def test_submission_immutability(self):
        doc = frappe.get_doc(
            {
                "doctype": "Recommendation Submission",
                "recommendation_request": self.request.name,
                "student_applicant": self.applicant.name,
                "recommendation_template": self.template,
                "recommender_name": "Test Recommender",
                "recommender_email": "recommender@example.com",
                "answers_json": "{}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Submission", doc.name))

        doc = frappe.get_doc("Recommendation Submission", doc.name)
        doc.answers_json = '{"new": "value"}'
        with self.assertRaises(frappe.ValidationError):
            doc.save()

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

    def _create_document_type(self, organization: str, school: str) -> str:
        code = f"rec_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Type {code}",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "is_repeatable": 0,
                "classification_slot": f"admissions_{frappe.scrub(code)}",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name

    def _create_template(self, organization: str, school: str, doc_type: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": f"Template {frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "target_document_type": doc_type,
                "minimum_required": 1,
                "maximum_allowed": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Template", doc.name))
        return doc.name

    def _create_applicant(self, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Applicant",
                "last_name": f"Test-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc

    def _create_request(self, applicant_name: str, template: str):
        doc = frappe.get_doc(
            {
                "doctype": "Recommendation Request",
                "student_applicant": applicant_name,
                "recommendation_template": template,
                "recommender_name": "Test Recommender",
                "recommender_email": "recommender@example.com",
                "expires_on": frappe.utils.add_days(frappe.utils.nowdate(), 7),
                "token_hash": frappe.generate_hash(length=32),
                "item_key": f"key_{frappe.generate_hash(length=6)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Request", doc.name))
        return doc
