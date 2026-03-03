# ifitwala_ed/admission/doctype/recommendation_request/test_recommendation_request.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRecommendationRequest(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self.organization = self._create_organization("Org-Req")
        self.school = self._create_school(self.organization, "School-Req")
        self.doc_type = self._create_document_type(self.organization, self.school)
        self.template = self._create_template(self.organization, self.school, self.doc_type)
        self.applicant = self._create_applicant(self.organization, self.school)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_links_and_scope_validation(self):
        # Missing target document type inside template (should ideally not happen, but the logic checks it)
        bad_template = self._create_template(self.organization, self.school, self.doc_type, active=0)
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Request",
                    "student_applicant": self.applicant.name,
                    "recommendation_template": bad_template,
                    "recommender_name": "Test Recommender",
                    "recommender_email": "recommender@example.com",
                    "expires_on": frappe.utils.add_days(frappe.utils.nowdate(), 7),
                    "token_hash": "hash123",
                    "item_key": "k1",
                }
            )
            doc.insert(ignore_permissions=True)

    def test_item_key_uniqueness_per_applicant(self):
        doc1 = frappe.get_doc(
            {
                "doctype": "Recommendation Request",
                "student_applicant": self.applicant.name,
                "recommendation_template": self.template,
                "recommender_name": "Test Recommender",
                "recommender_email": "recommender@example.com",
                "expires_on": frappe.utils.add_days(frappe.utils.nowdate(), 7),
                "token_hash": "hash123",
                "item_key": "unique_key",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Request", doc1.name))

        with self.assertRaises(frappe.ValidationError):
            doc2 = frappe.get_doc(
                {
                    "doctype": "Recommendation Request",
                    "student_applicant": self.applicant.name,
                    "recommendation_template": self.template,
                    "recommender_name": "Another Recommender",
                    "recommender_email": "another@example.com",
                    "expires_on": frappe.utils.add_days(frappe.utils.nowdate(), 7),
                    "token_hash": "hash456",
                    "item_key": "unique_key",
                }
            )
            doc2.insert(ignore_permissions=True)

    def test_stale_open_requests_are_expired_on_save(self):
        doc = frappe.get_doc(
            {
                "doctype": "Recommendation Request",
                "student_applicant": self.applicant.name,
                "recommendation_template": self.template,
                "recommender_name": "Test Recommender",
                "recommender_email": "recommender@example.com",
                "expires_on": frappe.utils.add_days(frappe.utils.nowdate(), -1),  # Past date
                "token_hash": frappe.generate_hash(length=32),
                "item_key": f"key_{frappe.generate_hash(length=6)}",
                "request_status": "Sent",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Request", doc.name))
        self.assertEqual(doc.request_status, "Expired")

    def test_immutability(self):
        doc = frappe.get_doc(
            {
                "doctype": "Recommendation Request",
                "student_applicant": self.applicant.name,
                "recommendation_template": self.template,
                "recommender_name": "Test Recommender",
                "recommender_email": "recommender@example.com",
                "expires_on": frappe.utils.add_days(frappe.utils.nowdate(), 7),
                "token_hash": "hash123",
                "item_key": "immutable_key",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Request", doc.name))

        doc = frappe.get_doc("Recommendation Request", doc.name)
        doc.item_key = "new_key"
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

    def _create_template(self, organization: str, school: str, doc_type: str, active: int = 1) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": f"Template {frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "target_document_type": doc_type,
                "minimum_required": 1,
                "maximum_allowed": 1,
                "is_active": active,
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
