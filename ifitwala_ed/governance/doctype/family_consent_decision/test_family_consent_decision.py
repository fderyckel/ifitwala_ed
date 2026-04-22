import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestFamilyConsentDecision(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.created: list[tuple[str, str]] = []

        self.organization = make_organization(prefix="FCD Org")
        self.created.append(("Organization", self.organization.name))
        self.school = make_school(self.organization.name, prefix="FCD School")
        self.created.append(("School", self.school.name))
        self.student = self._make_student()
        self.request_doc = self._make_request()

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
                    "student_first_name": "Paper",
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
                "request_title": "Paper Return Form",
                "request_type": "One-off Permission Request",
                "organization": self.organization.name,
                "school": self.school.name,
                "request_text": "<p>Bring back the signed form.</p>",
                "subject_scope": "Per Student",
                "audience_mode": "Guardian",
                "signer_rule": "Any Authorized Guardian",
                "decision_mode": "Approve / Decline",
                "completion_channel_mode": "Paper Only",
                "targets": [{"student": self.student.name}],
                "fields": [
                    {
                        "field_label": "Guardian Phone",
                        "field_type": "Phone",
                        "value_source": "Guardian.guardian_mobile_phone",
                        "field_mode": "Allow Override",
                    }
                ],
                "status": "Published",
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Family Consent Request", doc.name))
        return doc

    def test_paper_only_request_rejects_portal_decision_source(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Family Consent Decision",
                    "family_consent_request": self.request_doc.name,
                    "student": self.student.name,
                    "decision_by_doctype": "Guardian",
                    "decision_by": "GDN-0001",
                    "decision_status": "Approved",
                    "source_channel": "Guardian Portal",
                    "response_snapshot": "{}",
                }
            ).insert(ignore_permissions=True)

    def test_paper_only_request_allows_desk_paper_capture(self):
        decision = frappe.get_doc(
            {
                "doctype": "Family Consent Decision",
                "family_consent_request": self.request_doc.name,
                "student": self.student.name,
                "decision_by_doctype": "Guardian",
                "decision_by": "GDN-0001",
                "decision_status": "Approved",
                "source_channel": "Desk Paper Capture",
                "response_snapshot": "{}",
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Family Consent Decision", decision.name))

        self.assertEqual(decision.source_channel, "Desk Paper Capture")
