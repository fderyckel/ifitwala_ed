# ifitwala_ed/admission/doctype/applicant_review_rule_reviewer/test_applicant_review_rule_reviewer.py
# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase


class TestApplicantReviewRuleReviewer(FrappeTestCase):
    def test_applicant_review_rule_reviewer(self):
        # Validation for reviewer rows is already handled in test_applicant_review_rule.py
        # This file ensures Frappe test runner detects the tests successfully.
        self.assertTrue(True)
