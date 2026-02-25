# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/test_analytics_permissions.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.portal import _build_staff_home_capabilities
from ifitwala_ed.api.student_demographics_dashboard import _get_demographics_access_context


class TestAnalyticsPermissions(FrappeTestCase):
    def test_staff_home_demographics_capability_is_separate_from_admissions(self):
        caps = _build_staff_home_capabilities({"Accreditation Visitor"})
        self.assertTrue(caps.get("analytics_demographics"))
        self.assertFalse(caps.get("analytics_admissions"))
        self.assertFalse(caps.get("analytics_policy_signatures"))

    def test_demographics_access_allows_admission_officer_full_mode(self):
        with patch(
            "ifitwala_ed.api.student_demographics_dashboard.frappe.get_roles",
            return_value=["Admission Officer"],
        ):
            ctx = _get_demographics_access_context(user="admission-officer@example.com")
            self.assertEqual(ctx.get("mode"), "full")

    def test_demographics_access_allows_marketing_user_full_mode(self):
        with patch(
            "ifitwala_ed.api.student_demographics_dashboard.frappe.get_roles",
            return_value=["Marketing User"],
        ):
            ctx = _get_demographics_access_context(user="marketing@example.com")
            self.assertEqual(ctx.get("mode"), "full")

    def test_demographics_access_allows_accreditation_visitor_full_mode(self):
        with patch(
            "ifitwala_ed.api.student_demographics_dashboard.frappe.get_roles",
            return_value=["Accreditation Visitor"],
        ):
            ctx = _get_demographics_access_context(user="visitor@example.com")
            self.assertEqual(ctx.get("mode"), "full")

    def test_demographics_access_keeps_instructor_scoped_mode(self):
        with (
            patch(
                "ifitwala_ed.api.student_demographics_dashboard.frappe.get_roles",
                return_value=["Instructor"],
            ),
            patch(
                "ifitwala_ed.api.student_demographics_dashboard.frappe.db.sql",
                return_value=[[1]],
            ),
        ):
            ctx = _get_demographics_access_context(user="instructor@example.com")
            self.assertEqual(ctx.get("mode"), "instructor")

    def test_demographics_access_rejects_guest(self):
        with self.assertRaises(frappe.PermissionError):
            _get_demographics_access_context(user="Guest")

    def test_demographics_access_rejects_user_without_eligible_roles(self):
        with patch(
            "ifitwala_ed.api.student_demographics_dashboard.frappe.get_roles",
            return_value=["Employee"],
        ):
            with self.assertRaises(frappe.PermissionError):
                _get_demographics_access_context(user="staff@example.com")

    def test_staff_home_policy_signature_capabilities_for_hr(self):
        caps = _build_staff_home_capabilities({"HR Manager"})
        self.assertTrue(caps.get("analytics_policy_signatures"))
        self.assertTrue(caps.get("manage_policy_signatures"))
