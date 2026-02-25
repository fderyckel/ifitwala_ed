# ifitwala_ed/website/tests/test_portal_route.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.www.hub.index import get_context


class TestPortalRoute(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self.organization = self._create_organization().name

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_admissions_applicant_hitting_portal_namespace_redirects_to_admissions(self):
        user = self._create_user("admissions", roles=["Admissions Applicant"])
        original_request = self._set_request_path("/hub/admissions/status")
        frappe.set_user(user.name)
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/admissions")
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def test_guest_redirects_to_login_for_canonical_student_route(self):
        frappe.set_user("Guest")
        original_request = self._set_request_path("/hub/student/activities")
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=/hub/student/activities")
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def test_staff_hitting_student_namespace_redirects_to_staff_home(self):
        user = self._create_user("staff", roles=["Employee"])
        self._create_employee(user.name)
        original_request = self._set_request_path("/hub/student")
        frappe.set_user(user.name)
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/hub/staff")
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def test_administrator_role_with_inactive_employee_still_routes_to_staff_home(self):
        user = self._create_user("admin-inactive", roles=["Administrator"])
        self._create_employee(user.name, employment_status="Temporary Leave")
        original_request = self._set_request_path("/hub/student")
        frappe.set_user(user.name)
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/hub/staff")
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def test_staff_with_admissions_role_hitting_student_namespace_redirects_to_staff_home(self):
        user = self._create_user("staff-admissions", roles=["Administrator", "Admissions Applicant"])
        original_request = self._set_request_path("/hub/student")
        frappe.set_user(user.name)
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/hub/staff")
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _create_user(self, prefix: str, *, roles: list[str] | None = None):
        roles = roles or []
        for role in roles:
            self._ensure_role(role)
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"portal-route-{prefix}-{frappe.generate_hash(length=6)}@example.com",
                "first_name": "Portal",
                "last_name": "Route",
                "enabled": 1,
                "roles": [{"role": role} for role in roles],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user

    def _create_organization(self):
        org = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Portal Org {frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", org.name))
        return org

    def _create_employee(self, user_email: str, *, employment_status: str = "Active"):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Staff",
                "employee_last_name": f"Redirect {frappe.generate_hash(length=5)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user_email,
                "organization": self.organization,
                "date_of_joining": nowdate(),
                "employment_status": employment_status,
                "user_id": user_email,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", employee.name))
        return employee

    def _set_request_path(self, path: str):
        original = getattr(frappe.local, "request", None)
        frappe.local.request = frappe._dict(path=path)
        return original

    def _restore_request(self, original):
        if original is None:
            if hasattr(frappe.local, "request"):
                del frappe.local.request
            return
        frappe.local.request = original
