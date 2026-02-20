# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/test_users.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.api.users import (
    STAFF_ROLES,
    _strip_redirect_query,
    get_website_user_home_page,
    redirect_user_to_entry_portal,
)


class TestUserRedirect(FrappeTestCase):
    """Test unified login redirect logic."""

    def test_strip_redirect_query_removes_redirect_to_params(self):
        raw = "/login?redirect-to=%2Fapp&foo=bar&redirect_to=%2Fapp#frag"
        cleaned = _strip_redirect_query(raw)
        self.assertEqual(cleaned, "/login?foo=bar#frag")

    def test_all_users_redirect_to_staff_entry(self):
        """Standard users should be redirected to /portal/staff on login."""
        # Create test user
        user = frappe.new_doc("User")
        user.email = "test_user_portal@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.enabled = 1
        user.save()

        # Simulate login
        frappe.set_user(user.email)
        frappe.local.response = {}

        # Call redirect function
        redirect_user_to_entry_portal()

        # Assert redirect to /portal/staff
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("User", user.email, force=True)

    def test_admissions_applicant_redirects_to_admissions(self):
        """Admissions Applicants should be redirected to /admissions."""
        # Create test user with Admissions Applicant role
        user = frappe.new_doc("User")
        user.email = "test_admissions_applicant@example.com"
        user.first_name = "Test"
        user.last_name = "Admissions Applicant"
        user.enabled = 1
        user.add_roles("Admissions Applicant")
        user.save()

        # Simulate login
        frappe.set_user(user.email)
        frappe.local.response = {}

        # Call redirect function
        redirect_user_to_entry_portal()

        # Assert redirect to /admissions (separate admissions portal)
        self.assertEqual(frappe.local.response.get("home_page"), "/admissions")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/admissions")

        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("User", user.email, force=True)

    def test_login_redirect_does_not_persist_user_home_page(self):
        """Login redirect should be response-only and must not overwrite User.home_page."""
        user = frappe.new_doc("User")
        user.email = "test_no_home_page_persist@example.com"
        user.first_name = "No"
        user.last_name = "Persist"
        user.enabled = 1
        user.home_page = "/app"
        user.save()

        frappe.set_user(user.email)
        frappe.local.response = {}
        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        user.reload()
        self.assertEqual(user.home_page, "/app")

        frappe.set_user("Administrator")
        frappe.delete_doc("User", user.email, force=True)

    def test_login_redirect_normalizes_invalid_relative_home_page(self):
        """Invalid relative User.home_page values should be repaired to canonical portal routes."""
        user = frappe.new_doc("User")
        user.email = "test_normalize_relative_home_page@example.com"
        user.first_name = "Relative"
        user.last_name = "Home"
        user.enabled = 1
        user.home_page = "portal/student"
        user.add_roles("Student")
        user.save()

        frappe.set_user(user.email)
        frappe.local.response = {}
        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/student")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/student")

        user.reload()
        self.assertEqual(user.home_page, "/portal/student")

        frappe.set_user("Administrator")
        frappe.delete_doc("User", user.email, force=True)

    def test_login_redirect_overrides_incoming_redirect_to_param(self):
        """Role-based redirect must win over incoming redirect_to values like /app."""
        user = frappe.new_doc("User")
        user.email = "test_override_redirect_param@example.com"
        user.first_name = "Override"
        user.last_name = "Redirect"
        user.enabled = 1
        user.add_roles("Employee")
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Override"
        employee.last_name = "Redirect"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employment_status = "Active"
        employee.save()

        frappe.set_user(user.email)
        frappe.local.response = {}
        frappe.form_dict = frappe._dict({"redirect_to": "/app"})

        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")
        self.assertEqual(frappe.form_dict.get("redirect_to"), "/portal/staff")
        self.assertEqual(frappe.form_dict.get("redirect-to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_login_redirect_sets_login_manager_home_page(self):
        """Login hook must set login_manager.home_page to canonical portal target."""
        user = frappe.new_doc("User")
        user.email = "test_login_manager_home_page@example.com"
        user.first_name = "Home"
        user.last_name = "Page"
        user.enabled = 1
        user.add_roles("Employee")
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Home"
        employee.last_name = "Page"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employment_status = "Active"
        employee.save()

        class _LoginManager:
            def __init__(self):
                self.home_page = "/app"

        login_manager = _LoginManager()

        frappe.set_user(user.email)
        frappe.local.response = {}
        frappe.form_dict = frappe._dict({"redirect_to": "/app"})

        redirect_user_to_entry_portal(login_manager=login_manager)

        self.assertEqual(login_manager.home_page, "/portal/staff")
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_guardian_redirects_to_guardian_portal(self):
        """Guardians should be redirected to /portal/guardian."""
        # Create test user with Guardian role
        user = frappe.new_doc("User")
        user.email = "test_guardian_portal@example.com"
        user.first_name = "Test"
        user.last_name = "Guardian"
        user.enabled = 1
        user.add_roles("Guardian")
        user.save()

        # Create Guardian record linked to user
        guardian = frappe.new_doc("Guardian")
        guardian.guardian_first_name = "Test"
        guardian.guardian_last_name = "Guardian"
        guardian.guardian_email = user.email
        guardian.guardian_mobile_phone = "5550000001"
        guardian.user = user.email
        guardian.save()

        # Simulate login
        frappe.set_user(user.email)
        frappe.local.response = {}

        # Call redirect function
        redirect_user_to_entry_portal()

        # Assert redirect to guardian portal
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/guardian")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/guardian")

        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("Guardian", guardian.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_student_redirects_to_student_portal(self):
        """Students should be redirected to /portal/student."""
        # Create test user with Student role
        user = frappe.new_doc("User")
        user.email = "test_student_portal@example.com"
        user.first_name = "Test"
        user.last_name = "Student"
        user.enabled = 1
        user.add_roles("Student")
        user.save()

        # Create Student record linked to user
        student = frappe.new_doc("Student")
        student.student_first_name = "Test"
        student.student_last_name = "Student"
        student.student_email = user.email
        student.student_user_id = user.email
        previous_in_import = bool(getattr(frappe.flags, "in_import", False))
        frappe.flags.in_import = True
        try:
            student.save()
        finally:
            frappe.flags.in_import = previous_in_import

        # Simulate login
        frappe.set_user(user.email)
        frappe.local.response = {}

        # Call redirect function
        redirect_user_to_entry_portal()

        # Assert redirect to student portal
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/student")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/student")

        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("Student", student.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_staff_redirects_to_staff_portal(self):
        """Staff should be redirected to /portal/staff."""
        # Create test user with Employee role
        user = frappe.new_doc("User")
        user.email = "test_staff_portal@example.com"
        user.first_name = "Test"
        user.last_name = "Staff"
        user.enabled = 1
        user.add_roles("Employee")
        user.save()

        # Create Employee record linked to user
        employee = frappe.new_doc("Employee")
        employee.first_name = "Test"
        employee.last_name = "Staff"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employment_status = "Active"
        employee.save()

        # Simulate login
        frappe.set_user(user.email)
        frappe.local.response = {}

        # Call redirect function
        redirect_user_to_entry_portal()

        # Assert redirect to staff portal
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_employee_role_without_employee_profile_redirects_to_staff(self):
        """Employee role alone should route to /portal/staff."""
        user = frappe.new_doc("User")
        user.email = "test_employee_role_only_portal@example.com"
        user.first_name = "Employee"
        user.last_name = "RoleOnly"
        user.enabled = 1
        user.add_roles("Employee")
        user.save()

        frappe.set_user(user.email)
        frappe.local.response = {}

        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("User", user.email, force=True)

    def test_staff_role_without_employee_profile_redirects_to_staff(self):
        """Staff roles still route to /portal/staff even without Employee profile."""
        user = frappe.new_doc("User")
        user.email = "test_staff_role_only_portal@example.com"
        user.first_name = "Teacher"
        user.last_name = "RoleOnly"
        user.enabled = 1
        user.add_roles("Teacher")
        user.save()

        frappe.set_user(user.email)
        frappe.local.response = {}

        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("User", user.email, force=True)

    def test_active_employee_record_redirects_to_staff_even_without_employee_role(self):
        """Active employee profile should force /portal/staff even without Employee role."""
        user = frappe.new_doc("User")
        user.email = "test_active_employee_profile_redirect@example.com"
        user.first_name = "Active"
        user.last_name = "Employee"
        user.enabled = 1
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Active"
        employee.last_name = "Employee"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employment_status = "Active"
        employee.save()

        frappe.set_user(user.email)
        frappe.local.response = {}

        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_non_active_employee_profile_falls_back_to_staff(self):
        """Non-Active employee profile without student/guardian roles falls back to /portal/staff."""
        user = frappe.new_doc("User")
        user.email = "test_temp_leave_employee_profile_redirect@example.com"
        user.first_name = "Temporary"
        user.last_name = "Leave"
        user.enabled = 1
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Temporary"
        employee.last_name = "Leave"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employment_status = "Temporary Leave"
        employee.save()

        frappe.set_user(user.email)
        frappe.local.response = {}

        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_login_self_heals_active_employee_link_and_redirects_to_staff(self):
        """If user_id link is missing but active employee email matches, login should self-heal and route staff."""
        user = frappe.new_doc("User")
        user.email = "test_self_heal_employee_link@example.com"
        user.first_name = "Self"
        user.last_name = "Heal"
        user.enabled = 1
        user.add_roles("Employee")
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Self"
        employee.last_name = "Heal"
        employee.date_of_joining = nowdate()
        employee.employee_professional_email = user.email
        employee.employment_status = "Active"
        employee.save()

        frappe.set_user(user.email)
        frappe.local.response = {}

        redirect_user_to_entry_portal()

        employee.reload()
        self.assertEqual(employee.user_id, user.email)
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_unlinked_active_employee_email_match_routes_to_staff(self):
        """Active employee email match should resolve staff portal even when user_id link is missing."""
        user = frappe.new_doc("User")
        user.email = "test_unlinked_active_employee_email_match@example.com"
        user.first_name = "Unlinked"
        user.last_name = "Active"
        user.enabled = 1
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Unlinked"
        employee.last_name = "Active"
        employee.date_of_joining = nowdate()
        employee.employee_professional_email = user.email
        employee.employment_status = "Active"
        employee.save()

        frappe.set_user(user.email)
        frappe.local.response = {}

        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_guest_user_ignored(self):
        """Guest users should not trigger redirect."""
        frappe.set_user("Guest")
        frappe.local.response = {}

        # Call redirect function
        redirect_user_to_entry_portal()

        # Assert no redirect was set
        self.assertNotIn("home_page", frappe.local.response)
        self.assertNotIn("redirect_to", frappe.local.response)

        # Cleanup
        frappe.set_user("Administrator")

    def test_get_website_user_home_page_uses_canonical_policy(self):
        """Website home hook should resolve to canonical portal/staff for active staff users."""
        user = frappe.new_doc("User")
        user.email = "test_website_home_policy@example.com"
        user.first_name = "Web"
        user.last_name = "Home"
        user.enabled = 1
        user.add_roles("Employee")
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Web"
        employee.last_name = "Home"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employment_status = "Active"
        employee.save()

        frappe.set_user(user.email)
        self.assertEqual(get_website_user_home_page(), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_logout_flow_does_not_force_redirect_exception(self):
        """Logout-triggered on_login must not raise Redirect."""
        user = frappe.new_doc("User")
        user.email = "test_logout_no_redirect_exception@example.com"
        user.first_name = "Logout"
        user.last_name = "Safe"
        user.enabled = 1
        user.add_roles("Employee")
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Logout"
        employee.last_name = "Safe"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employment_status = "Active"
        employee.save()

        frappe.set_user(user.email)
        frappe.local.response = {}

        original_path = getattr(frappe.request, "path", None)
        original_form_dict = getattr(frappe, "form_dict", None)
        original_in_test = bool(getattr(frappe.flags, "in_test", False))
        try:
            frappe.request.path = "/api/method/logout"
            frappe.form_dict = frappe._dict({"cmd": "logout"})
            frappe.flags.in_test = False

            redirect_user_to_entry_portal()

            self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
            self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")
        finally:
            frappe.flags.in_test = original_in_test
            if original_form_dict is None:
                frappe.form_dict = frappe._dict()
            else:
                frappe.form_dict = original_form_dict
            if original_path is not None:
                frappe.request.path = original_path
            frappe.set_user("Administrator")
            frappe.delete_doc("Employee", employee.name, force=True)
            frappe.delete_doc("User", user.email, force=True)

    def test_staff_roles_constant(self):
        """Verify STAFF_ROLES contains expected roles."""
        expected_roles = {
            "Employee",
            "Academic User",
            "System Manager",
            "Teacher",
            "Administrator",
            "Finance User",
            "HR User",
            "HR Manager",
        }
        self.assertEqual(STAFF_ROLES, expected_roles)
