# ifitwala_ed/api/test_admissions_portal_facade.py

from unittest import TestCase

import frappe

from ifitwala_ed.api import admissions_portal


class TestAdmissionsPortalFacade(TestCase):
    def test_session_endpoint_remains_whitelisted(self):
        self.assertIn(admissions_portal.get_admissions_session, frappe.whitelisted)
