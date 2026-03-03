# ifitwala_ed/admission/doctype/recommendation_template/test_recommendation_template.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRecommendationTemplate(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created = []
        self.organization = self._create_organization("Org-Recomm")
        self.school = self._create_school(self.organization, "School-Recomm")
        self.doc_type_repeatable = self._create_document_type(self.organization, self.school, "rec_rep", 1)
        self.doc_type_single = self._create_document_type(self.organization, self.school, "rec_sin", 0)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_scope_validation(self):
        other_org = self._create_organization("Other-Org")
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Template",
                    "template_name": "Test Template",
                    "organization": other_org,
                    "school": self.school,
                    "target_document_type": self.doc_type_single,
                }
            )
            doc.insert(ignore_permissions=True)

    def test_limits_validation(self):
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Template",
                    "template_name": "Test Template",
                    "organization": self.organization,
                    "school": self.school,
                    "target_document_type": self.doc_type_single,
                    "minimum_required": -1,
                    "maximum_allowed": 1,
                }
            )
            doc.insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Template",
                    "template_name": "Test Template",
                    "organization": self.organization,
                    "school": self.school,
                    "target_document_type": self.doc_type_single,
                    "minimum_required": 2,
                    "maximum_allowed": 1,
                }
            )
            doc.insert(ignore_permissions=True)

    def test_file_upload_rules(self):
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Template",
                    "template_name": "Test Template",
                    "organization": self.organization,
                    "school": self.school,
                    "target_document_type": self.doc_type_single,
                    "file_upload_required": 1,
                    "allow_file_upload": 0,
                }
            )
            doc.insert(ignore_permissions=True)

    def test_target_document_type_must_be_repeatable_if_max_allowed_is_greater_than_1(self):
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Template",
                    "template_name": "Test Template",
                    "organization": self.organization,
                    "school": self.school,
                    "target_document_type": self.doc_type_single,
                    "minimum_required": 1,
                    "maximum_allowed": 2,
                }
            )
            doc.insert(ignore_permissions=True)

    def test_template_fields_validation(self):
        # Missing field key
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Template",
                    "template_name": "Test Template",
                    "organization": self.organization,
                    "school": self.school,
                    "target_document_type": self.doc_type_single,
                    "template_fields": [{"label": "Name", "field_type": "Data"}],
                }
            )
            doc.insert(ignore_permissions=True)

        # Duplicate field key
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Template",
                    "template_name": "Test Template",
                    "organization": self.organization,
                    "school": self.school,
                    "target_document_type": self.doc_type_single,
                    "template_fields": [
                        {"field_key": "name", "label": "Name", "field_type": "Data"},
                        {"field_key": "name", "label": "Name 2", "field_type": "Data"},
                    ],
                }
            )
            doc.insert(ignore_permissions=True)

        # Select field without options
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Recommendation Template",
                    "template_name": "Test Template",
                    "organization": self.organization,
                    "school": self.school,
                    "target_document_type": self.doc_type_single,
                    "template_fields": [{"field_key": "rating", "label": "Rating", "field_type": "Select"}],
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

    def _create_document_type(self, organization: str, school: str, prefix: str, is_repeatable: int) -> str:
        code = f"{prefix}_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": f"Type {code}",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "is_repeatable": is_repeatable,
                "classification_slot": f"admissions_{frappe.scrub(code)}",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name
