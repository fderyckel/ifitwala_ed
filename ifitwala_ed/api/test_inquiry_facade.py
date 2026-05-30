# ifitwala_ed/api/test_inquiry_facade.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import inquiry


class TestInquiryFacade(TestCase):
    def test_inquiry_facade_preserves_public_method_delegation(self):
        with patch("ifitwala_ed.admission.api.inquiry.lookups.get_inquiry_types", return_value=["Admissions"]) as impl:
            self.assertEqual(inquiry.get_inquiry_types(), ["Admissions"])

        impl.assert_called_once_with()

    def test_public_guest_link_queries_remain_whitelisted(self):
        self.assertIn(inquiry.inquiry_organization_link_query, frappe.whitelisted)
        self.assertIn(inquiry.inquiry_school_link_query, frappe.whitelisted)
        self.assertIn(inquiry.get_inquiry_acknowledgement_context, frappe.whitelisted)
        self.assertTrue(getattr(inquiry.inquiry_organization_link_query, "allow_guest", False))
        self.assertTrue(getattr(inquiry.inquiry_school_link_query, "allow_guest", False))
        self.assertTrue(getattr(inquiry.get_inquiry_acknowledgement_context, "allow_guest", False))
