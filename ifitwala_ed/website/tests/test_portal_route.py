# ifitwala_ed/website/tests/test_portal_route.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.www.portal.index import get_context


class TestPortalRoute(FrappeTestCase):
    def test_admissions_applicant_hitting_portal_namespace_redirects_to_admissions(self):
        user = frappe.new_doc("User")
        user.email = "test_portal_admissions_canonical@example.com"
        user.first_name = "Admissions"
        user.last_name = "Canonical"
        user.enabled = 1
        user.add_roles("Admissions Applicant")
        user.save()

        applicant = frappe.new_doc("Student Applicant")
        applicant.first_name = "Admissions"
        applicant.last_name = "Canonical"
        applicant.applicant_user = user.email
        applicant.save()

        original_path = getattr(frappe.request, "path", None)
        frappe.request.path = "/portal/admissions/status"
        frappe.set_user(user.email)

        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())

            self.assertEqual(
                frappe.local.flags.redirect_location,
                "/admissions",
            )
        finally:
            frappe.set_user("Administrator")
            if original_path is not None:
                frappe.request.path = original_path
            frappe.delete_doc("Student Applicant", applicant.name, force=True)
            frappe.delete_doc("User", user.email, force=True)

    def test_guest_redirects_to_login_for_canonical_student_route(self):
        frappe.set_user("Guest")
        original_path = getattr(frappe.request, "path", None)
        frappe.request.path = "/portal/student/activities"

        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())

            self.assertEqual(
                frappe.local.flags.redirect_location,
                "/login?redirect-to=/portal/student/activities",
            )
        finally:
            frappe.set_user("Administrator")
            if original_path is not None:
                frappe.request.path = original_path

    def test_legacy_top_level_student_route_redirects_to_canonical_namespace(self):
        user = frappe.new_doc("User")
        user.email = "test_portal_legacy_student@example.com"
        user.first_name = "Legacy"
        user.last_name = "Student"
        user.enabled = 1
        user.add_roles("Student")
        user.save()

        student = frappe.new_doc("Student")
        student.first_name = "Legacy"
        student.last_name = "Student"
        student.student_email = user.email
        student.student_user_id = user.email
        student.save()

        original_path = getattr(frappe.request, "path", None)
        frappe.request.path = "/student/activities"
        frappe.set_user(user.email)

        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())

            self.assertEqual(
                frappe.local.flags.redirect_location,
                "/portal/student/activities",
            )
        finally:
            frappe.set_user("Administrator")
            if original_path is not None:
                frappe.request.path = original_path
            frappe.delete_doc("Student", student.name, force=True)
            frappe.delete_doc("User", user.email, force=True)

    def test_staff_hitting_student_namespace_redirects_to_staff_home(self):
        user = frappe.new_doc("User")
        user.email = "test_portal_staff_redirect@example.com"
        user.first_name = "Staff"
        user.last_name = "Redirect"
        user.enabled = 1
        user.add_roles("Employee")
        user.save()

        employee = frappe.new_doc("Employee")
        employee.first_name = "Staff"
        employee.last_name = "Redirect"
        employee.user_id = user.email
        employee.employment_status = "Active"
        employee.save()

        original_path = getattr(frappe.request, "path", None)
        frappe.request.path = "/portal/student"
        frappe.set_user(user.email)

        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())

            self.assertEqual(
                frappe.local.flags.redirect_location,
                "/portal/staff",
            )
        finally:
            frappe.set_user("Administrator")
            if original_path is not None:
                frappe.request.path = original_path
            frappe.delete_doc("Employee", employee.name, force=True)
            frappe.delete_doc("User", user.email, force=True)
