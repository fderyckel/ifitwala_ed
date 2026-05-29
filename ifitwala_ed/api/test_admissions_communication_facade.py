# ifitwala_ed/api/test_admissions_communication_facade.py

from unittest import TestCase

import frappe

from ifitwala_ed.api import admissions_communication


class TestAdmissionsCommunicationFacade(TestCase):
    def test_case_thread_endpoints_allow_guest_to_reach_auth_guard(self):
        self.assertIn(admissions_communication.send_admissions_case_message, frappe.whitelisted)
        self.assertIn(admissions_communication.get_admissions_case_thread, frappe.whitelisted)
        self.assertIn(admissions_communication.mark_admissions_case_thread_read, frappe.whitelisted)
        self.assertTrue(bool(getattr(admissions_communication.send_admissions_case_message, "allow_guest", False)))
        self.assertTrue(bool(getattr(admissions_communication.get_admissions_case_thread, "allow_guest", False)))
        self.assertTrue(bool(getattr(admissions_communication.mark_admissions_case_thread_read, "allow_guest", False)))
