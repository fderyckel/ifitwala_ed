# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/test_users.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

try:
    from werkzeug.routing import RequestRedirect
except Exception:
    from werkzeug.routing.exceptions import RequestRedirect

from ifitwala_ed.api.users import (
    STAFF_ROLES,
    _strip_redirect_query,
    get_website_user_home_page,
    redirect_non_staff_away_from_desk,
    redirect_user_to_entry_portal,
    sanitize_login_redirect_param,
)


def _ensure_test_organization() -> str:
    name = frappe.db.get_value("Organization", {"organization_name": "Redirect Test Org"}, "name")
    if name:
        return name
    doc = frappe.get_doc(
        {
            "doctype": "Organization",
            "organization_name": "Redirect Test Org",
            "abbr": f"R{frappe.generate_hash(length=4)}",
        }
    ).insert(ignore_permissions=True)
    return doc.name


def _ensure_role(role: str) -> None:
    if frappe.db.exists("Role", role):
        return
    frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)


def _append_role(user_doc, role: str) -> None:
    _ensure_role(role)
    user_doc.append("roles", {"role": role})


class TestUserRedirect(FrappeTestCase):
    """Test unified login redirect logic."""

    def _user_has_home_page_field(self) -> bool:
        try:
            return bool(frappe.get_meta("User").has_field("home_page"))
        except Exception:
            return False

    def test_strip_redirect_query_removes_redirect_to_params(self):
        raw = "/login?redirect-to=%2Fapp&foo=bar&redirect_to=%2Fapp#frag"
        cleaned = _strip_redirect_query(raw)
        self.assertEqual(cleaned, "/login?foo=bar#frag")

    def test_sanitize_login_redirect_param_cleans_app_subpaths(self):
        original_request = getattr(frappe.local, "request", None)
        original_form_dict = getattr(frappe, "form_dict", None)
        try:
            frappe.local.request = frappe._dict(
                path="/login",
                method="GET",
                full_path="/login?redirect-to=%2Fapp%2Feca&foo=bar",
                args={"redirect-to": "/app/eca"},
            )
            frappe.form_dict = frappe._dict({"redirect_to": "/app/eca"})
            with self.assertRaises(RequestRedirect) as ctx:
                sanitize_login_redirect_param()
            self.assertEqual(getattr(ctx.exception, "new_url", None), "/login?foo=bar")
            self.assertEqual(frappe.form_dict.get("redirect_to"), "")
            self.assertEqual(frappe.form_dict.get("redirect-to"), "")
        finally:
            if original_request is None:
                if hasattr(frappe.local, "request"):
                    del frappe.local.request
            else:
                frappe.local.request = original_request
            if original_form_dict is None:
                if hasattr(frappe, "form_dict"):
                    delattr(frappe, "form_dict")
            else:
                frappe.form_dict = original_form_dict

    def test_non_staff_desk_request_redirects_admissions_applicant(self):
        user = frappe.new_doc("User")
        user.email = f"test_admissions_desk_block_{frappe.generate_hash(length=6)}@example.com"
        user.first_name = "Admissions"
        user.last_name = "Applicant"
        user.enabled = 1
        _append_role(user, "Admissions Applicant")
        user.insert(ignore_permissions=True)

        original_request = getattr(frappe.local, "request", None)
        try:
            frappe.set_user(user.email)
            frappe.local.request = frappe._dict(path="/app/eca", method="GET")
            with self.assertRaises(RequestRedirect) as ctx:
                redirect_non_staff_away_from_desk()
            self.assertEqual(getattr(ctx.exception, "new_url", None), "/admissions")
        finally:
            if original_request is None:
                if hasattr(frappe.local, "request"):
                    del frappe.local.request
            else:
                frappe.local.request = original_request
            frappe.set_user("Administrator")
            frappe.delete_doc("User", user.email, force=True)

    def test_staff_role_with_admissions_role_is_not_redirected_from_desk(self):
        user = frappe.new_doc("User")
        user.email = f"test_staff_plus_admissions_{frappe.generate_hash(length=6)}@example.com"
        user.first_name = "Mixed"
        user.last_name = "Roles"
        user.enabled = 1
        _append_role(user, "Administrator")
        _append_role(user, "Admissions Applicant")
        user.insert(ignore_permissions=True)

        original_request = getattr(frappe.local, "request", None)
        try:
            frappe.set_user(user.email)
            frappe.local.flags.redirect_location = None
            frappe.local.request = frappe._dict(path="/app/eca", method="GET")
            redirect_non_staff_away_from_desk()
            self.assertIsNone(frappe.local.flags.redirect_location)
        finally:
            if original_request is None:
                if hasattr(frappe.local, "request"):
                    del frappe.local.request
            else:
                frappe.local.request = original_request
            frappe.set_user("Administrator")
            frappe.delete_doc("User", user.email, force=True)

    def test_staff_desk_request_is_not_redirected(self):
        user = frappe.new_doc("User")
        user.email = f"test_staff_desk_allow_{frappe.generate_hash(length=6)}@example.com"
        user.first_name = "Desk"
        user.last_name = "Staff"
        user.enabled = 1
        _append_role(user, "Employee")
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Desk"
        employee.employee_last_name = "Staff"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employee_professional_email = user.email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

        original_request = getattr(frappe.local, "request", None)
        try:
            frappe.set_user(user.email)
            frappe.local.flags.redirect_location = None
            frappe.local.request = frappe._dict(path="/app/eca", method="GET")
            redirect_non_staff_away_from_desk()
            self.assertIsNone(frappe.local.flags.redirect_location)
        finally:
            if original_request is None:
                if hasattr(frappe.local, "request"):
                    del frappe.local.request
            else:
                frappe.local.request = original_request
            frappe.set_user("Administrator")
            frappe.delete_doc("Employee", employee.name, force=True)
            frappe.delete_doc("User", user.email, force=True)

    def test_all_users_redirect_to_staff_entry(self):
        """Standard users should be redirected to /portal/staff on login."""
        # Create test user
        user = frappe.new_doc("User")
        user.email = "test_user_portal@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.enabled = 1
        user.insert(ignore_permissions=True)

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
        _append_role(user, "Admissions Applicant")
        user.insert(ignore_permissions=True)

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

    def test_staff_and_admissions_roles_redirect_to_staff(self):
        """Mixed staff+admissions roles must prefer staff routing."""
        user = frappe.new_doc("User")
        user.email = f"test_staff_admissions_precedence_{frappe.generate_hash(length=6)}@example.com"
        user.first_name = "Staff"
        user.last_name = "Admissions"
        user.enabled = 1
        _append_role(user, "Administrator")
        _append_role(user, "Admissions Applicant")
        user.insert(ignore_permissions=True)

        frappe.set_user(user.email)
        frappe.local.response = {}

        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("User", user.email, force=True)

    def test_login_redirect_does_not_persist_user_home_page(self):
        """Login redirect should be response-only and must not overwrite User.home_page."""
        user = frappe.new_doc("User")
        user.email = "test_no_home_page_persist@example.com"
        user.first_name = "No"
        user.last_name = "Persist"
        user.enabled = 1
        if self._user_has_home_page_field():
            user.home_page = "/app"
        user.insert(ignore_permissions=True)

        frappe.set_user(user.email)
        frappe.local.response = {}
        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        if self._user_has_home_page_field():
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
        if self._user_has_home_page_field():
            user.home_page = "portal/student"
        _append_role(user, "Student")
        user.insert(ignore_permissions=True)

        frappe.set_user(user.email)
        frappe.local.response = {}
        redirect_user_to_entry_portal()

        self.assertEqual(frappe.local.response.get("home_page"), "/portal/student")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/student")

        if self._user_has_home_page_field():
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
        _append_role(user, "Employee")
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Override"
        employee.employee_last_name = "Redirect"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employee_professional_email = user.email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

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
        _append_role(user, "Employee")
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Home"
        employee.employee_last_name = "Page"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employee_professional_email = user.email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

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
        _append_role(user, "Guardian")
        user.insert(ignore_permissions=True)

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
        _append_role(user, "Student")
        user.insert(ignore_permissions=True)

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
        _append_role(user, "Employee")
        user.insert(ignore_permissions=True)

        # Create Employee record linked to user
        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Test"
        employee.employee_last_name = "Staff"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employee_professional_email = user.email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

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
        _append_role(user, "Employee")
        user.insert(ignore_permissions=True)

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
        _append_role(user, "Teacher")
        user.insert(ignore_permissions=True)

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
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Active"
        employee.employee_last_name = "Employee"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employee_professional_email = user.email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

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
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Temporary"
        employee.employee_last_name = "Leave"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employee_professional_email = user.email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Temporary Leave"
        employee.insert(ignore_permissions=True)

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
        email = f"test_self_heal_employee_link_{frappe.generate_hash(length=6)}@example.com"
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = "Self"
        user.last_name = "Heal"
        user.enabled = 1
        _append_role(user, "Employee")
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Self"
        employee.employee_last_name = "Heal"
        employee.date_of_joining = nowdate()
        employee.employee_professional_email = email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

        frappe.set_user(user.email)
        frappe.local.response = {}

        redirect_user_to_entry_portal()

        employee.reload()
        self.assertEqual(employee.user_id, email)
        self.assertEqual(frappe.local.response.get("home_page"), "/portal/staff")
        self.assertEqual(frappe.local.response.get("redirect_to"), "/portal/staff")

        frappe.set_user("Administrator")
        frappe.delete_doc("Employee", employee.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_unlinked_active_employee_email_match_routes_to_staff(self):
        """Active employee email match should resolve staff portal even when user_id link is missing."""
        email = f"test_unlinked_active_employee_{frappe.generate_hash(length=6)}@example.com"
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = "Unlinked"
        user.last_name = "Active"
        user.enabled = 1
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Unlinked"
        employee.employee_last_name = "Active"
        employee.date_of_joining = nowdate()
        employee.employee_professional_email = email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

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
        _append_role(user, "Employee")
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Web"
        employee.employee_last_name = "Home"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employee_professional_email = user.email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

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
        _append_role(user, "Employee")
        user.insert(ignore_permissions=True)

        employee = frappe.new_doc("Employee")
        employee.employee_first_name = "Logout"
        employee.employee_last_name = "Safe"
        employee.date_of_joining = nowdate()
        employee.user_id = user.email
        employee.employee_professional_email = user.email
        employee.organization = _ensure_test_organization()
        employee.employment_status = "Active"
        employee.insert(ignore_permissions=True)

        frappe.set_user(user.email)
        frappe.local.response = {}

        original_request = getattr(frappe.local, "request", None)
        original_form_dict = getattr(frappe, "form_dict", None)
        original_in_test = bool(getattr(frappe.flags, "in_test", False))
        try:
            frappe.local.request = frappe._dict(path="/api/method/logout", method="POST")
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
            if original_request is None:
                if hasattr(frappe.local, "request"):
                    del frappe.local.request
            else:
                frappe.local.request = original_request
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
