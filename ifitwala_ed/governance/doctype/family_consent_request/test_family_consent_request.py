from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestFamilyConsentRequest(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.created: list[tuple[str, str]] = []

        self.organization = make_organization(prefix="FCR Org")
        self.created.append(("Organization", self.organization.name))
        self.school = make_school(self.organization.name, prefix="FCR School")
        self.created.append(("School", self.school.name))
        self.student = self._make_student()

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self.created):
            if not frappe.db.exists(doctype, name):
                continue
            frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def _make_student(self):
        seed = frappe.generate_hash(length=6)
        previous_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Student",
                    "student_first_name": "Freeze",
                    "student_last_name": seed,
                    "student_email": f"freeze-{seed}@example.com",
                    "anchor_school": self.school.name,
                    "allow_direct_creation": 1,
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = previous_import
        self.created.append(("Student", doc.name))
        return doc

    def _make_request(self):
        doc = frappe.get_doc(
            {
                "doctype": "Family Consent Request",
                "request_title": "Media Consent",
                "request_type": "Mutable Consent",
                "organization": self.organization.name,
                "school": self.school.name,
                "request_text": "<p>Consent text</p>",
                "subject_scope": "Per Student",
                "audience_mode": "Student",
                "signer_rule": "Student Self",
                "decision_mode": "Grant / Deny",
                "completion_channel_mode": "Paper Only",
                "targets": [{"student": self.student.name}],
                "fields": [
                    {
                        "field_label": "Student Email",
                        "field_type": "Email",
                        "value_source": "Student.student_email",
                        "field_mode": "Allow Override",
                        "allow_profile_writeback": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Family Consent Request", doc.name))
        return doc

    def _make_source_file(self):
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"consent-{frappe.generate_hash(length=6)}.pdf",
                "is_private": 1,
                "content": b"consent",
            }
        ).insert(ignore_permissions=True)
        self.created.append(("File", file_doc.name))
        return file_doc

    def test_request_populates_target_scope_from_student(self):
        request_doc = self._make_request()

        self.assertEqual(request_doc.targets[0].school, self.school.name)
        self.assertEqual(request_doc.targets[0].organization, self.organization.name)
        self.assertTrue(request_doc.fields[0].field_key)

    def test_published_request_content_is_frozen(self):
        request_doc = self._make_request()
        request_doc.status = "Published"
        request_doc.save(ignore_permissions=True)

        request_doc.request_title = "Updated title"
        with self.assertRaises(frappe.ValidationError):
            request_doc.save(ignore_permissions=True)

    def test_request_rejects_non_governed_source_file(self):
        source_file = self._make_source_file()
        with patch(
            "ifitwala_ed.governance.doctype.family_consent_request.family_consent_request.is_governed_file",
            return_value=False,
        ):
            with self.assertRaises(frappe.ValidationError):
                frappe.get_doc(
                    {
                        "doctype": "Family Consent Request",
                        "request_title": "Field Trip",
                        "request_type": "One-off Permission Request",
                        "organization": self.organization.name,
                        "school": self.school.name,
                        "request_text": "<p>Trip details</p>",
                        "source_file": source_file.name,
                        "subject_scope": "Per Student",
                        "audience_mode": "Guardian",
                        "signer_rule": "Any Authorized Guardian",
                        "decision_mode": "Approve / Decline",
                        "completion_channel_mode": "Portal Only",
                        "targets": [{"student": self.student.name}],
                        "fields": [
                            {
                                "field_label": "Guardian Phone",
                                "field_type": "Phone",
                                "value_source": "Guardian.guardian_mobile_phone",
                                "field_mode": "Allow Override",
                            }
                        ],
                    }
                ).insert(ignore_permissions=True)
