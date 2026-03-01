# ifitwala_ed/admission/doctype/applicant_document_type/test_applicant_document_type.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.admission_utils import has_complete_applicant_document_type_classification


class TestApplicantDocumentType(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_active_document_type_with_complete_classification_is_allowed(self):
        organization = self._create_organization("Admissions Org")
        school = self._create_school(organization=organization, prefix="Admissions School")
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"passport_{frappe.generate_hash(length=6)}",
                "document_type_name": "Passport",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "classification_slot": "identity_passport",
                "classification_data_class": "legal",
                "classification_purpose": "identification_document",
                "classification_retention_policy": "until_school_exit_plus_6m",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))

    def test_active_unmapped_code_requires_classification_fields(self):
        organization = self._create_organization("Admissions Org")
        school = self._create_school(organization=organization, prefix="Admissions School")

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Applicant Document Type",
                    "code": f"custom_{frappe.generate_hash(length=8)}",
                    "document_type_name": "Custom Required Doc",
                    "organization": organization,
                    "school": school,
                    "is_active": 1,
                }
            ).insert(ignore_permissions=True)

    def test_active_mapped_code_autofills_classification_fields(self):
        if frappe.db.exists("Applicant Document Type", "id_documents"):
            self.skipTest("id_documents exists on site; skipping mapped autofill test.")

        organization = self._create_organization("Admissions Org")
        school = self._create_school(organization=organization, prefix="Admissions School")

        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": "id_documents",
                "document_type_name": "ID Documents",
                "organization": organization,
                "school": school,
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))

        self.assertEqual(doc.classification_slot, "identity_passport")
        self.assertEqual(doc.classification_data_class, "legal")
        self.assertEqual(doc.classification_purpose, "identification_document")
        self.assertEqual(doc.classification_retention_policy, "until_school_exit_plus_6m")

    def test_mapped_code_is_treated_as_upload_configured(self):
        self.assertTrue(has_complete_applicant_document_type_classification({"code": "transcript"}))
        self.assertTrue(has_complete_applicant_document_type_classification({"code": "id_documents"}))
        self.assertFalse(has_complete_applicant_document_type_classification({"code": "custom_unmapped"}))

    def test_non_repeatable_document_type_forces_min_items_to_one(self):
        organization = self._create_organization("Admissions Org")
        school = self._create_school(organization=organization, prefix="Admissions School")
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"single_file_{frappe.generate_hash(length=6)}",
                "document_type_name": "Single File",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "is_repeatable": 0,
                "min_items_required": 4,
                "classification_slot": f"single_{frappe.generate_hash(length=4)}",
                "classification_data_class": "administrative",
                "classification_purpose": "administrative",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))

        self.assertEqual(int(doc.min_items_required), 1)

    def test_repeatable_document_type_coerces_min_items_to_positive(self):
        organization = self._create_organization("Admissions Org")
        school = self._create_school(organization=organization, prefix="Admissions School")
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": f"repeat_file_{frappe.generate_hash(length=6)}",
                "document_type_name": "Repeatable File",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "is_repeatable": 1,
                "min_items_required": 0,
                "classification_slot": f"repeat_{frappe.generate_hash(length=4)}",
                "classification_data_class": "academic",
                "classification_purpose": "academic_report",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))

        self.assertEqual(int(doc.min_items_required), 1)

    def test_school_scope_must_match_selected_organization_scope(self):
        root_org = self._create_organization("Root Org", is_group=1)
        child_org = self._create_organization("Child Org", parent=root_org)
        sibling_org = self._create_organization("Sibling Org")
        school = self._create_school(organization=child_org, prefix="Child School")

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Applicant Document Type",
                    "code": f"passport_{frappe.generate_hash(length=6)}",
                    "document_type_name": "Passport",
                    "organization": sibling_org,
                    "school": school,
                    "is_active": 1,
                }
            ).insert(ignore_permissions=True)

    def _create_organization(self, prefix: str, parent: str | None = None, is_group: int = 0) -> str:
        organization = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix}-{frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=5)}",
                "is_group": int(is_group),
                "parent_organization": parent,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", organization.name))
        return organization.name

    def _create_school(self, *, organization: str, prefix: str) -> str:
        school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{prefix}-{frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=5)}",
                "organization": organization,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", school.name))
        return school.name
