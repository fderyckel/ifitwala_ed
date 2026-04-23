import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.family_consent_staff import (
    get_family_consent_dashboard,
    get_family_consent_dashboard_context,
    publish_family_consent_request,
)
from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestFamilyConsentStaff(FrappeTestCase):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        self.created: list[tuple[str, str]] = []

        self.organization = make_organization(prefix="FC Org")
        self.created.append(("Organization", self.organization.name))
        self.school = make_school(self.organization.name, prefix="FC School")
        self.created.append(("School", self.school.name))

        self.student_one = self._make_student(email_prefix="one")
        self.student_two = self._make_student(email_prefix="two")

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self.created):
            if not frappe.db.exists(doctype, name):
                continue
            frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
        super().tearDown()

    def _make_student(self, *, email_prefix: str):
        seed = frappe.generate_hash(length=6)
        previous_migration = bool(getattr(frappe.flags, "in_migration", False))
        frappe.flags.in_migration = True
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Student",
                    "student_first_name": "Consent",
                    "student_last_name": f"{email_prefix}-{seed}",
                    "student_email": f"{email_prefix}-{seed}@example.com",
                    "anchor_school": self.school.name,
                }
            ).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_migration = previous_migration
        self.created.append(("Student", doc.name))
        return doc

    def _make_request(self, *, title: str, completion_channel_mode: str = "Portal Only", due_on: str | None = None):
        doc = frappe.get_doc(
            {
                "doctype": "Family Consent Request",
                "request_title": title,
                "request_type": "One-off Permission Request",
                "organization": self.organization.name,
                "school": self.school.name,
                "request_text": "<p>Review this request.</p>",
                "subject_scope": "Per Student",
                "audience_mode": "Guardian",
                "signer_rule": "Any Authorized Guardian",
                "decision_mode": "Approve / Decline",
                "completion_channel_mode": completion_channel_mode,
                "due_on": due_on,
                "targets": [
                    {"student": self.student_one.name},
                    {"student": self.student_two.name},
                ],
                "fields": [
                    {
                        "field_label": "Emergency Phone",
                        "field_type": "Phone",
                        "value_source": "Guardian.primary_phone",
                        "field_mode": "Allow Override",
                        "required": 1,
                        "allow_profile_writeback": 1,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Family Consent Request", doc.name))
        return doc

    def test_publish_family_consent_request_sets_status_and_returns_counts(self):
        request_doc = self._make_request(title="Field Trip")

        payload = publish_family_consent_request(request_doc.name)

        request_doc.reload()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "published")
        self.assertEqual(request_doc.status, "Published")
        self.assertTrue(request_doc.request_key)
        self.assertEqual(payload["target_count"], 2)

    def test_dashboard_context_returns_scoped_filter_options(self):
        payload = get_family_consent_dashboard_context(organization=self.organization.name)

        self.assertEqual(payload["filters"]["organization"], self.organization.name)
        self.assertEqual(payload["options"]["organizations"], [self.organization.name])
        self.assertEqual(payload["options"]["schools"], [self.school.name])
        self.assertEqual(
            payload["options"]["completion_channel_modes"],
            ["Portal Only", "Portal Or Paper", "Paper Only"],
        )

    def test_dashboard_reports_completion_channel_and_derived_counts(self):
        published = self._make_request(
            title="Paper Optional Trip",
            completion_channel_mode="Portal Or Paper",
            due_on="2026-04-01",
        )
        publish_family_consent_request(published.name)

        approved = frappe.get_doc(
            {
                "doctype": "Family Consent Decision",
                "family_consent_request": published.name,
                "student": self.student_one.name,
                "decision_by_doctype": "Guardian",
                "decision_by": "GDN-0001",
                "decision_status": "Approved",
                "source_channel": "Guardian Portal",
                "response_snapshot": "{}",
            }
        ).insert(ignore_permissions=True)
        self.created.append(("Family Consent Decision", approved.name))

        payload = get_family_consent_dashboard(organization=self.organization.name)

        self.assertEqual(payload["counts"]["requests"], 1)
        self.assertEqual(payload["counts"]["completed"], 1)
        self.assertEqual(payload["counts"]["overdue"], 1)
        self.assertEqual(payload["rows"][0]["completion_channel_mode"], "Portal Or Paper")
        self.assertEqual(payload["rows"][0]["completed_count"], 1)
        self.assertEqual(payload["rows"][0]["overdue_count"], 1)

    def test_dashboard_rejects_school_outside_selected_organization(self):
        other_organization = make_organization(prefix="FC Other Org")
        self.created.append(("Organization", other_organization.name))
        other_school = make_school(other_organization.name, prefix="FC Other School")
        self.created.append(("School", other_school.name))

        with self.assertRaises(frappe.PermissionError):
            get_family_consent_dashboard(
                organization=self.organization.name,
                school=other_school.name,
            )
