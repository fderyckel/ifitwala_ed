# ifitwala_ed/admission/doctype/recommendation_template/test_recommendation_template.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import hashlib

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

    def test_target_document_type_is_auto_created_when_missing(self):
        template = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": "Auto Template",
                "organization": self.organization,
                "school": self.school,
                "minimum_required": 1,
                "maximum_allowed": 2,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Template", template.name))

        target_name = (template.target_document_type or "").strip()
        self.assertTrue(bool(target_name))
        self._created.append(("Applicant Document Type", target_name))

        target_row = frappe.db.get_value(
            "Applicant Document Type",
            target_name,
            [
                "code",
                "organization",
                "school",
                "is_repeatable",
                "is_required",
                "classification_slot",
                "classification_data_class",
                "classification_purpose",
                "classification_retention_policy",
            ],
            as_dict=True,
        )
        self.assertTrue(bool(target_row))
        self.assertEqual(target_row.get("code"), self._managed_target_code())
        self.assertEqual(target_row.get("organization"), self.organization)
        self.assertEqual(target_row.get("school"), self.school)
        self.assertEqual(int(target_row.get("is_repeatable") or 0), 1)
        self.assertEqual(int(target_row.get("is_required") or 0), 0)
        self.assertEqual(target_row.get("classification_slot"), "recommendation_letter")
        self.assertEqual(target_row.get("classification_data_class"), "academic")
        self.assertEqual(target_row.get("classification_purpose"), "academic_report")
        self.assertEqual(target_row.get("classification_retention_policy"), "until_program_end_plus_1y")

    def test_missing_target_reuses_same_managed_document_type(self):
        first = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": "Auto Template A",
                "organization": self.organization,
                "school": self.school,
                "minimum_required": 1,
                "maximum_allowed": 2,
            }
        ).insert(ignore_permissions=True)
        second = frappe.get_doc(
            {
                "doctype": "Recommendation Template",
                "template_name": "Auto Template B",
                "organization": self.organization,
                "school": self.school,
                "minimum_required": 1,
                "maximum_allowed": 3,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Recommendation Template", first.name))
        self._created.append(("Recommendation Template", second.name))

        self.assertEqual(first.target_document_type, second.target_document_type)
        self._created.append(("Applicant Document Type", first.target_document_type))

        count = frappe.db.count(
            "Applicant Document Type",
            {"code": self._managed_target_code()},
        )
        self.assertEqual(count, 1)

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

    def _managed_target_code(self) -> str:
        seed = f"{self.organization}|{self.school}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
        return f"recommendation_letter_{digest}"
