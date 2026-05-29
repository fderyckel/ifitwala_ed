# ifitwala_ed/api/test_recommendation_intake_facade.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import recommendation_intake


class TestRecommendationIntakeFacade(TestCase):
    def test_facade_preserves_public_method_delegation(self):
        with patch(
            "ifitwala_ed.admission.api.recommendation_intake.list_recommendation_templates",
            return_value={"templates": []},
        ) as impl:
            self.assertEqual(
                recommendation_intake.list_recommendation_templates(student_applicant="APP-0001"),
                {"templates": []},
            )

        impl.assert_called_once_with(student_applicant="APP-0001")

    def test_public_guest_intake_methods_remain_whitelisted(self):
        self.assertIn(recommendation_intake.get_recommendation_intake_payload, frappe.whitelisted)
        self.assertIn(recommendation_intake.send_recommendation_otp, frappe.whitelisted)
        self.assertIn(recommendation_intake.verify_recommendation_otp, frappe.whitelisted)
        self.assertIn(recommendation_intake.submit_recommendation, frappe.whitelisted)
        self.assertTrue(getattr(recommendation_intake.get_recommendation_intake_payload, "allow_guest", False))
        self.assertTrue(getattr(recommendation_intake.send_recommendation_otp, "allow_guest", False))
        self.assertTrue(getattr(recommendation_intake.verify_recommendation_otp, "allow_guest", False))
        self.assertTrue(getattr(recommendation_intake.submit_recommendation, "allow_guest", False))
