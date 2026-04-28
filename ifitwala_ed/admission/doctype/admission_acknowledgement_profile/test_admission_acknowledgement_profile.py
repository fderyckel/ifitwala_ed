# ifitwala_ed/admission/doctype/admission_acknowledgement_profile/test_admission_acknowledgement_profile.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.inquiry_acknowledgement import (
    build_public_acknowledgement_context,
    queue_inquiry_family_acknowledgement,
    send_inquiry_family_acknowledgement,
)
from ifitwala_ed.api.inquiry import inquiry_school_link_query


class TestAdmissionAcknowledgementProfile(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_public_context_uses_school_profile_and_visit_cta(self):
        organization = self._make_organization()
        school = self._make_school(
            organization=organization,
            school_name="Context School",
            is_published=1,
            website_slug="context-school",
            admissions_visit_route="/schools/context-school/visit",
        )
        template = self._make_email_template()
        self._make_profile(
            organization=organization,
            school=school.name,
            email_template=template.name,
            thank_you_message="Thanks for reaching out to Context School.",
            visit_cta_route="",
        )

        payload = build_public_acknowledgement_context(
            organization=organization,
            school=school.name,
            type_of_inquiry="Admission",
        )

        self.assertEqual(payload["brand"]["name"], "Context School")
        self.assertEqual(payload["message"], "Thanks for reaching out to Context School.")
        self.assertIn("timeline", payload)
        self.assertIn(
            {"kind": "visit", "label": "Book a tour or open day", "url": "/schools/context-school/visit"},
            payload["ctas"],
        )
        self.assertFalse([cta for cta in payload["ctas"] if cta.get("kind") == "application"])

    def test_application_cta_rejects_authenticated_admissions_portal(self):
        organization = self._make_organization()
        school = self._make_school(organization=organization)
        template = self._make_email_template()

        with self.assertRaises(frappe.ValidationError):
            self._make_profile(
                organization=organization,
                school=school.name,
                email_template=template.name,
                show_application_cta=1,
                application_cta_route="/admissions",
            )

    def test_public_school_query_exposes_only_inquiry_enabled_schools(self):
        organization = self._make_organization(get_inquiry=1)
        unpublished_enabled = self._make_school(
            organization=organization,
            school_name="Enabled Inquiry School",
            is_published=0,
            show_in_inquiry=1,
        )
        published_but_hidden = self._make_school(
            organization=organization,
            school_name="Hidden Inquiry School",
            is_published=1,
            show_in_inquiry=0,
        )

        rows = inquiry_school_link_query(txt="Inquiry School", filters={"organization": organization})
        names = {row[0] for row in rows}

        self.assertIn(unpublished_enabled.name, names)
        self.assertNotIn(published_but_hidden.name, names)

    def test_queue_uses_short_after_commit_for_public_web_form(self):
        previous = getattr(frappe.flags, "in_web_form", None)
        frappe.flags.in_web_form = True
        try:
            with patch("ifitwala_ed.admission.inquiry_acknowledgement.frappe.enqueue") as mocked_enqueue:
                queue_inquiry_family_acknowledgement(
                    frappe._dict(
                        {
                            "doctype": "Inquiry",
                            "name": "INQ-TEST-ACK",
                            "email": "family@example.com",
                        }
                    )
                )
        finally:
            frappe.flags.in_web_form = previous

        mocked_enqueue.assert_called_once()
        self.assertEqual(
            mocked_enqueue.call_args.args[0],
            "ifitwala_ed.admission.inquiry_acknowledgement.send_inquiry_family_acknowledgement",
        )
        self.assertEqual(mocked_enqueue.call_args.kwargs["queue"], "short")
        self.assertTrue(mocked_enqueue.call_args.kwargs["enqueue_after_commit"])
        self.assertEqual(mocked_enqueue.call_args.kwargs["inquiry_name"], "INQ-TEST-ACK")

    def test_send_acknowledgement_renders_school_template(self):
        organization = self._make_organization()
        school = self._make_school(
            organization=organization,
            school_name="Mail School",
            is_published=1,
            website_slug="mail-school",
        )
        template = self._make_email_template(
            subject="Thanks {{ doc.first_name }}",
            response_="Hello {{ doc.first_name }} from {{ brand.name }}.",
        )
        self._make_profile(organization=organization, school=school.name, email_template=template.name)
        inquiry = self._make_inquiry(
            organization=organization,
            school=school.name,
            email="mail-family@example.com",
            first_name="Mira",
        )

        with patch("ifitwala_ed.admission.inquiry_acknowledgement.frappe.sendmail") as mocked_sendmail:
            result = send_inquiry_family_acknowledgement(inquiry.name)

        self.assertTrue(result["sent"])
        self.assertEqual(mocked_sendmail.call_args.kwargs["recipients"], ["mail-family@example.com"])
        self.assertEqual(mocked_sendmail.call_args.kwargs["subject"], "Thanks Mira")
        self.assertIn("Hello Mira from Mail School.", mocked_sendmail.call_args.kwargs["message"])
        self.assertEqual(mocked_sendmail.call_args.kwargs["reference_doctype"], "Inquiry")
        self.assertEqual(mocked_sendmail.call_args.kwargs["reference_name"], inquiry.name)

    def _make_organization(self, *, get_inquiry: int = 0) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Ack Org {frappe.generate_hash(length=6)}",
                "abbr": f"AO{frappe.generate_hash(length=4)}",
                "get_inquiry": get_inquiry,
            }
        )
        doc.insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _make_school(
        self,
        *,
        organization: str,
        school_name: str | None = None,
        is_published: int = 0,
        show_in_inquiry: int = 0,
        website_slug: str | None = None,
        admissions_visit_route: str | None = None,
    ):
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": school_name or f"Ack School {frappe.generate_hash(length=6)}",
                "abbr": f"AS{frappe.generate_hash(length=4)}",
                "organization": organization,
                "is_published": is_published,
                "show_in_inquiry": show_in_inquiry,
                "website_slug": website_slug,
                "admissions_visit_route": admissions_visit_route,
            }
        )
        doc.insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc

    def _make_email_template(
        self,
        *,
        subject: str = "We received your inquiry",
        response_: str = "Thank you for contacting us.",
    ):
        template_name = f"Ack Template {frappe.generate_hash(length=8)}"
        doc = frappe.get_doc(
            {
                "doctype": "Email Template",
                "name": template_name,
                "email_template_name": template_name,
                "subject": subject,
                "response_": response_,
            }
        )
        doc.insert(ignore_permissions=True)
        self._created.append(("Email Template", doc.name))
        return doc

    def _make_profile(self, **kwargs):
        payload = {
            "doctype": "Admission Acknowledgement Profile",
            "profile_name": f"Ack Profile {frappe.generate_hash(length=6)}",
            "is_active": 1,
            "organization": kwargs["organization"],
            "school": kwargs.get("school"),
            "email_template": kwargs["email_template"],
            "thank_you_message": kwargs.get("thank_you_message"),
            "visit_cta_route": kwargs.get("visit_cta_route"),
            "show_application_cta": kwargs.get("show_application_cta", 0),
            "application_cta_route": kwargs.get("application_cta_route"),
        }
        doc = frappe.get_doc(payload)
        doc.insert(ignore_permissions=True)
        self._created.append(("Admission Acknowledgement Profile", doc.name))
        return doc

    def _make_inquiry(
        self,
        *,
        organization: str,
        school: str,
        email: str,
        first_name: str,
    ):
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": first_name,
                "last_name": "Family",
                "email": email,
                "organization": organization,
                "school": school,
                "type_of_inquiry": "Admission",
                "message": "Please send more information.",
            }
        )
        doc.insert(ignore_permissions=True)
        self._created.append(("Inquiry", doc.name))
        return doc
