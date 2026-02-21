# ifitwala_ed/website/tests/test_admissions_portal_route.py

from urllib.parse import quote

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.www.admissions.index import get_context


class TestAdmissionsPortalRoute(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_guest_redirects_to_login(self):
        frappe.set_user("Guest")
        original_request = self._set_request_path("/admissions")
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/login?redirect-to=/admissions")
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def test_authenticated_non_admissions_user_is_logged_out_before_login_redirect(self):
        user = self._create_user("non-role")
        original_request = self._set_request_path("/admissions")
        frappe.set_user(user.name)
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            expected_login = "/login?redirect-to=/admissions"
            self.assertEqual(
                frappe.local.flags.redirect_location,
                f"/logout?redirect-to={quote(expected_login, safe='')}",
            )
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def test_admissions_user_without_linked_applicant_is_logged_out_before_login_redirect(self):
        user = self._create_user("missing-applicant", roles=["Admissions Applicant"])
        original_request = self._set_request_path("/admissions")
        frappe.set_user(user.name)
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            expected_login = "/login?redirect-to=/admissions"
            self.assertEqual(
                frappe.local.flags.redirect_location,
                f"/logout?redirect-to={quote(expected_login, safe='')}",
            )
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def test_linked_admissions_user_loads_admissions_context(self):
        user = self._create_user("linked", roles=["Admissions Applicant"])
        applicant = self._create_student_applicant(user.name)
        original_request = self._set_request_path("/admissions")
        frappe.set_user(user.name)
        try:
            context = frappe._dict()
            result = get_context(context)
            self.assertEqual(result.applicant, applicant.name)
            self.assertEqual(result.title, "Admissions Portal")
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _create_user(self, prefix: str, roles: list[str] | None = None):
        roles = roles or []
        for role in roles:
            self._ensure_role(role)
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"admissions-route-{prefix}-{frappe.generate_hash(length=6)}@example.com",
                "first_name": "Admissions",
                "last_name": "Route",
                "enabled": 1,
                "roles": [{"role": role} for role in roles],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user

    def _create_student_applicant(self, applicant_user: str):
        self._ensure_role("Admission Manager")
        if not frappe.db.exists("Has Role", {"parent": "Administrator", "role": "Admission Manager"}):
            frappe.get_doc(
                {
                    "doctype": "Has Role",
                    "parent": "Administrator",
                    "parenttype": "User",
                    "parentfield": "roles",
                    "role": "Admission Manager",
                }
            ).insert(ignore_permissions=True)
        frappe.clear_cache(user="Administrator")

        org = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Admissions Org {frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", org.name))
        school = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"Admissions School {frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": org.name,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", school.name))

        applicant = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Linked",
                "last_name": "Applicant",
                "organization": org.name,
                "school": school.name,
                "application_status": "Draft",
            }
        ).insert(ignore_permissions=True)
        applicant.db_set("applicant_user", applicant_user, update_modified=False)
        applicant.reload()
        self._created.append(("Student Applicant", applicant.name))
        return applicant

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
