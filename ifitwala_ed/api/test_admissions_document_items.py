# ifitwala_ed/api/test_admissions_document_items.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

import base64

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.admissions_portal import list_applicant_documents, upload_applicant_document


class TestAdmissionsDocumentItems(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Admissions Applicant")

        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant_user = self._create_applicant_user()
        self.applicant = self._create_applicant(self.organization, self.school, self.applicant_user)
        self.document_type = self._create_document_type(self.organization, self.school)

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_upload_creates_item_and_returns_item_metadata(self):
        frappe.set_user(self.applicant_user)
        payload = upload_applicant_document(
            student_applicant=self.applicant.name,
            document_type=self.document_type,
            item_key="aisl_2019",
            item_label="AISL transcript 2019",
            file_name="aisl-2019.pdf",
            content=self._tiny_file_base64(),
        )

        self.assertTrue(bool(payload.get("applicant_document")))
        self.assertTrue(bool(payload.get("applicant_document_item")))
        self.assertEqual(payload.get("item_key"), "aisl_2019")
        self.assertEqual(payload.get("item_label"), "AISL transcript 2019")

        row = frappe.db.get_value(
            "Applicant Document Item",
            payload.get("applicant_document_item"),
            ["applicant_document", "item_key", "item_label"],
            as_dict=True,
        )
        self.assertTrue(bool(row))
        self.assertEqual(row.get("item_key"), "aisl_2019")
        self.assertEqual(row.get("item_label"), "AISL transcript 2019")

    def test_repeatable_upload_keeps_multiple_items(self):
        frappe.set_user(self.applicant_user)
        upload_applicant_document(
            student_applicant=self.applicant.name,
            document_type=self.document_type,
            item_key="aisl_2019",
            item_label="AISL transcript 2019",
            file_name="aisl-2019.pdf",
            content=self._tiny_file_base64(),
        )
        upload_applicant_document(
            student_applicant=self.applicant.name,
            document_type=self.document_type,
            item_key="isl_2020",
            item_label="ISL transcript 2020",
            file_name="isl-2020.pdf",
            content=self._tiny_file_base64(),
        )

        payload = list_applicant_documents(student_applicant=self.applicant.name)
        documents = payload.get("documents") or []
        self.assertEqual(len(documents), 1)

        items = documents[0].get("items") or []
        self.assertEqual(len(items), 2)
        labels = {row.get("item_label") for row in items}
        self.assertIn("AISL transcript 2019", labels)
        self.assertIn("ISL transcript 2020", labels)

    def test_upload_requires_item_description_for_new_item(self):
        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            upload_applicant_document(
                student_applicant=self.applicant.name,
                document_type=self.document_type,
                file_name="unknown.pdf",
                content=self._tiny_file_base64(),
            )

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

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
        email = f"portal-doc-item-{frappe.generate_hash(length=8)}@example.com"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Portal",
                "last_name": "Applicant",
                "enabled": 1,
                "roles": [{"role": "Admissions Applicant"}],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        frappe.clear_cache(user=user.name)
        return user.name

    def _create_applicant(self, organization: str, school: str, applicant_user: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Portal",
                "last_name": f"Docs-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
                "applicant_user": applicant_user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Student Applicant", doc.name))
        return doc

    def _create_document_type(self, organization: str, school: str) -> str:
        code = f"transcript_{frappe.generate_hash(length=6)}"
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Type",
                "code": code,
                "document_type_name": "Transcript",
                "organization": organization,
                "school": school,
                "is_active": 1,
                "is_required": 1,
                "is_repeatable": 1,
                "min_items_required": 2,
                "classification_slot": "prior_transcript",
                "classification_data_class": "academic",
                "classification_purpose": "academic_report",
                "classification_retention_policy": "until_program_end_plus_1y",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Type", doc.name))
        return doc.name

    def _tiny_file_base64(self) -> str:
        return base64.b64encode(b"test-file-content").decode("ascii")
