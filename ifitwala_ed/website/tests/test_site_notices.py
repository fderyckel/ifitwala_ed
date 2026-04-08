from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website.site_notices import get_active_site_notice, invalidate_site_notice_cache


class TestSiteNotices(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        invalidate_site_notice_cache()

    def tearDown(self):
        invalidate_site_notice_cache()

    def test_active_notice_returns_sanitized_public_payload(self):
        organization = make_organization(prefix="Notice Org")
        school = make_school(organization.name, prefix="Notice School")
        school.website_slug = f"notice-{frappe.generate_hash(length=6)}"
        school.is_published = 1
        school.save(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Website Notice",
                "title": "Admissions Alert",
                "school": school.name,
                "style": "warning",
                "workflow_state": "Published",
                "message_html": "<p>Campus tour registration is open.</p><script>alert('x')</script>",
                "button_label": "Register",
                "button_link": "/admissions",
            }
        ).insert(ignore_permissions=True)

        notice = get_active_site_notice(school_name=school.name)

        self.assertEqual(notice["title"], "Admissions Alert")
        self.assertEqual(notice["style"], "warning")
        self.assertIn("Campus tour registration is open.", notice["message_html"])
        self.assertNotIn("<script", notice["message_html"])
        self.assertEqual(notice["button_link"], "/admissions")
