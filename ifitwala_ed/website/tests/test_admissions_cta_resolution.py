from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.website.utils import resolve_admissions_cta_url


class TestAdmissionsCtaResolution(FrappeTestCase):
    def test_visit_falls_back_to_inquiry_route_when_missing(self):
        school = frappe._dict(
            {
                "admissions_inquiry_route": "/apply/inquiry",
                "admissions_apply_route": "/admissions",
                "admissions_visit_route": "",
            }
        )

        self.assertEqual(resolve_admissions_cta_url(school=school, intent="visit"), "/apply/inquiry")

    def test_apply_falls_back_to_admissions_portal_when_missing(self):
        school = frappe._dict(
            {
                "admissions_inquiry_route": "",
                "admissions_apply_route": "",
                "admissions_visit_route": "",
            }
        )

        self.assertEqual(resolve_admissions_cta_url(school=school, intent="apply"), "/admissions")
