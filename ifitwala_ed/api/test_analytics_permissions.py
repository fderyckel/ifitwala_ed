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

    def test_demographics_access_allows_academic_assistant_full_mode(self):
        with patch(
            "ifitwala_ed.api.student_demographics_dashboard.frappe.get_roles",
            return_value=["Academic Assistant"],
        ):
            ctx = _get_demographics_access_context(user="academic-assistant@example.com")
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

    def test_staff_home_academic_load_capability_for_academic_admin(self):
        caps = _build_staff_home_capabilities({"Academic Admin"})
        self.assertTrue(caps.get("analytics_academic_load"))

    def test_staff_home_demographics_capability_for_academic_assistant(self):
        caps = _build_staff_home_capabilities({"Academic Assistant"})
        self.assertTrue(caps.get("analytics_demographics"))

    def test_staff_home_student_overview_capability_for_academic_assistant(self):
        caps = _build_staff_home_capabilities({"Academic Assistant"})
        self.assertFalse(caps.get("analytics_student_overview"))

    def test_staff_home_student_overview_capability_for_instructor(self):
        caps = _build_staff_home_capabilities({"Instructor"})
        self.assertTrue(caps.get("analytics_student_overview"))

    def test_staff_home_academic_load_capability_is_hidden_from_instructor(self):
        caps = _build_staff_home_capabilities({"Instructor"})
        self.assertFalse(caps.get("analytics_academic_load"))

    def test_staff_home_policy_library_capability_for_employee(self):
        caps = _build_staff_home_capabilities({"Employee"})
        self.assertTrue(caps.get("staff_policy_library"))

    def test_staff_home_quick_actions_for_instructor(self):
        caps = _build_staff_home_capabilities({"Instructor"})
        self.assertTrue(caps.get("quick_action_create_task"))
        self.assertTrue(caps.get("quick_action_gradebook"))
        self.assertFalse(caps.get("quick_action_student_log"))
        self.assertFalse(caps.get("quick_action_create_event"))
        self.assertFalse(caps.get("quick_action_create_meeting"))
        self.assertFalse(caps.get("quick_action_create_school_event"))
        self.assertFalse(caps.get("quick_action_org_communication"))

    def test_staff_home_quick_actions_for_academic_staff(self):
        caps = _build_staff_home_capabilities({"Academic Staff"})
        self.assertFalse(caps.get("quick_action_create_task"))
        self.assertFalse(caps.get("quick_action_gradebook"))
        self.assertTrue(caps.get("quick_action_student_log"))
        self.assertFalse(caps.get("quick_action_create_event"))
        self.assertFalse(caps.get("quick_action_create_meeting"))
        self.assertFalse(caps.get("quick_action_create_school_event"))
        self.assertTrue(caps.get("quick_action_org_communication"))

    def test_staff_home_quick_actions_for_employee_meeting_creation(self):
        caps = _build_staff_home_capabilities({"Employee"})
        self.assertTrue(caps.get("quick_action_create_meeting"))
        self.assertFalse(caps.get("quick_action_create_school_event"))
        self.assertTrue(caps.get("quick_action_create_event"))
        self.assertTrue(caps.get("quick_action_org_communication"))

    def test_staff_home_quick_actions_for_school_event_roles(self):
        caps = _build_staff_home_capabilities({"Academic Admin"})
        self.assertFalse(caps.get("quick_action_create_meeting"))
        self.assertTrue(caps.get("quick_action_create_school_event"))
        self.assertTrue(caps.get("quick_action_create_event"))
        self.assertTrue(caps.get("quick_action_org_communication"))

    def test_staff_home_professional_development_capabilities_for_employee(self):
        caps = _build_staff_home_capabilities({"Employee"})
        self.assertTrue(caps.get("staff_professional_development"))
        self.assertFalse(caps.get("professional_development_decide"))
        self.assertFalse(caps.get("professional_development_liquidate"))

    def test_staff_home_professional_development_capabilities_for_finance(self):
        caps = _build_staff_home_capabilities({"Accounts Manager"})
        self.assertFalse(caps.get("staff_professional_development"))
        self.assertFalse(caps.get("professional_development_decide"))
        self.assertTrue(caps.get("professional_development_liquidate"))

    def test_staff_home_professional_development_capabilities_for_hr(self):
        caps = _build_staff_home_capabilities({"HR Manager"})
        self.assertTrue(caps.get("staff_professional_development"))
        self.assertTrue(caps.get("professional_development_decide"))
        self.assertFalse(caps.get("professional_development_liquidate"))
