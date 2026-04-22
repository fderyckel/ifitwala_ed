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
        previous_import = getattr(frappe.flags, "in_import", False)
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Student",
                    "student_first_name": "Freeze",
                    "student_last_name": frappe.generate_hash(length=6),
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
