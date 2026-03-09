# ifitwala_ed/admission/doctype/applicant_document_item/test_applicant_document_item.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApplicantDocumentItem(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Admissions Applicant")
        self._ensure_role("Admission Officer")
        self._ensure_role("System Manager")

        self.organization = self._create_organization()
        self.school = self._create_school(self.organization)
        self.applicant_user = self._create_applicant_user()
        self.admission_officer_user = self._create_staff_user("Admission Officer")
        self.applicant = self._create_applicant(self.organization, self.school, self.applicant_user)
        self.document_type = self._create_document_type(self.organization, self.school)
        self.applicant_document = self._create_applicant_document()

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_missing_or_invalid_applicant_document_throws_error(self):
        frappe.set_user(self.admission_officer_user)
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {"doctype": "Applicant Document Item", "item_key": "some_key", "item_label": "Some Key"}
            )
            doc.insert(ignore_permissions=True)

        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc(
                {
                    "doctype": "Applicant Document Item",
                    "applicant_document": "Invalid Doc",
                    "item_key": "some_key",
                    "item_label": "Some Key",
                }
            )
            doc.insert(ignore_permissions=True)

    def test_item_key_is_required_and_unique_per_document(self):
        frappe.set_user(self.admission_officer_user)
        doc1 = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": self.applicant_document,
                "item_key": "unique_key_1",
                "item_label": "Unique Key 1",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", doc1.name))

        with self.assertRaises(frappe.ValidationError):
            doc2 = frappe.get_doc(
                {
                    "doctype": "Applicant Document Item",
                    "applicant_document": self.applicant_document,
                    "item_key": "unique_key_1",
                    "item_label": "Unique Key 1 Duplicate",
                }
            )
            doc2.insert(ignore_permissions=True)

    def test_applicant_can_create_document_item(self):
        frappe.set_user(self.applicant_user)
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": self.applicant_document,
                "item_key": "applicant_file",
                "item_label": "Applicant File",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", doc.name))
        self.assertTrue(doc.name)

    def test_applicant_cannot_review_document_item(self):
        doc = self._create_item("test_review_key")
        frappe.set_user(self.applicant_user)
        doc = frappe.get_doc("Applicant Document Item", doc.name)
        doc.review_status = "Approved"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_admission_officer_can_review_document_item(self):
        doc = self._create_item("test_officer_review_key")
        frappe.set_user(self.admission_officer_user)
        doc = frappe.get_doc("Applicant Document Item", doc.name)
        doc.review_status = "Approved"
        doc.save(ignore_permissions=True)

        self.assertEqual(doc.review_status, "Approved")
        self.assertEqual(doc.reviewed_by, self.admission_officer_user)
        self.assertTrue(doc.reviewed_on)

    def test_immutable_fields_cannot_be_changed(self):
        doc = self._create_item("immutable_key")
        frappe.set_user(self.admission_officer_user)
        doc = frappe.get_doc("Applicant Document Item", doc.name)

        doc.item_key = "new_key"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_cannot_delete_with_attached_files_unless_system_manager(self):
        doc = self._create_item("file_key")

        # Attach a file
        frappe.set_user(self.admission_officer_user)
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": "test.txt",
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": doc.name,
                "content": b"hello",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("File", file_doc.name))

        # Officer cannot delete it
        frappe.set_user(self.admission_officer_user)
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("Applicant Document Item", doc.name, ignore_permissions=True)

        # System Manager can delete it
        frappe.set_user("Administrator")
        frappe.delete_doc("Applicant Document Item", doc.name, ignore_permissions=True)
        # Should not raise
        self.assertFalse(frappe.db.exists("Applicant Document Item", doc.name))

    def test_cannot_edit_if_applicant_is_rejected_or_promoted(self):
        doc = self._create_item("state_key")

        frappe.set_user("Administrator")
        applicant_doc = frappe.get_doc("Student Applicant", self.applicant.name)
        applicant_doc.db_set("application_status", "Rejected", update_modified=False)

        frappe.set_user(self.admission_officer_user)
        doc = frappe.get_doc("Applicant Document Item", doc.name)
        doc.item_label = "Updated Label"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

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
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Admission",
                "employee_last_name": role.replace(" ", ""),
                "employee_professional_email": email,
                "organization": self.organization,
                "school": self.school,
                "user_id": doc.name,
                "date_of_joining": frappe.utils.nowdate(),
                "employment_status": "Active",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", employee.name))
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
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        doc.db_set("applicant_user", applicant_user, update_modified=False)
        doc.db_set("application_status", "Invited", update_modified=False)
        doc.reload()
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

    def _create_applicant_document(self) -> str:
        frappe.set_user("Administrator")
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document",
                "student_applicant": self.applicant.name,
                "document_type": self.document_type,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document", doc.name))
        return doc.name

    def _create_item(self, item_key: str):
        frappe.set_user("Administrator")
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Document Item",
                "applicant_document": self.applicant_document,
                "item_key": item_key,
                "item_label": item_key.replace("_", " ").title(),
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Applicant Document Item", doc.name))
        return doc
