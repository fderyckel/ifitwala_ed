# ifitwala_ed/website/tests/test_admissions_portal_route.py

from urllib.parse import quote

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.www.admissions.index import get_context


def _admission_settings_has_field(fieldname: str) -> bool:
    if not frappe.db.exists("DocType", "Admission Settings"):
        return False
    return bool(frappe.get_meta("Admission Settings").has_field(fieldname))


class TestAdmissionsPortalRoute(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._access_mode_before = (
            frappe.db.get_single_value("Admission Settings", "admissions_access_mode")
            if _admission_settings_has_field("admissions_access_mode")
            else None
        )
        self.organization = self._create_organization().name

    def tearDown(self):
        frappe.set_user("Administrator")
        if _admission_settings_has_field("admissions_access_mode"):
            frappe.db.set_single_value(
                "Admission Settings",
                "admissions_access_mode",
                self._access_mode_before or "Single Applicant Workspace",
            )
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

    def test_staff_user_hitting_admissions_is_redirected_to_staff_portal(self):
        user = self._create_user("staff-only", roles=["Employee"])
        self._create_employee(user.name)
        original_request = self._set_request_path("/admissions")
        frappe.set_user(user.name)
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/hub/staff")
        finally:
            frappe.set_user("Administrator")
            self._restore_request(original_request)

    def test_staff_with_admissions_role_without_applicant_redirects_to_staff_portal(self):
        user = self._create_user("staff-admissions", roles=["Employee", "Admissions Applicant"])
        self._create_employee(user.name)
        original_request = self._set_request_path("/admissions")
        frappe.set_user(user.name)
        try:
            with self.assertRaises(frappe.Redirect):
                get_context(frappe._dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/hub/staff")
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

    def test_family_workspace_user_loads_admissions_context(self):
        if not _admission_settings_has_field("admissions_access_mode"):
            self.skipTest("Admission Settings.admissions_access_mode is required for family workspace tests.")

        self._set_admissions_access_mode("Family Workspace")
        user = self._create_user("family", roles=["Admissions Family"])
        guardian = self._create_guardian(user.name)
        applicant = self._create_student_applicant("")
        applicant.append(
            "guardians",
            {
                "guardian": guardian.name,
                "user": user.name,
                "relationship": "Mother",
                "can_consent": 1,
                "is_primary": 1,
                "guardian_first_name": "Family",
                "guardian_last_name": "Route",
                "guardian_email": user.name,
                "guardian_mobile_phone": "+14155550131",
                "guardian_image": "/private/files/family-route.png",
            },
        )
        applicant.save(ignore_permissions=True)

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
                "send_welcome_email": 0,
                "send_password_notification": 0,
                "roles": [{"role": role} for role in roles],
            }
        )
        user.flags.no_welcome_mail = True
        user = user.insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user

    def _create_organization(self):
        org = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Admissions Route Org {frappe.generate_hash(length=6)}",
                "abbr": f"A{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", org.name))
        return org

    def _create_employee(self, user_email: str):
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Admissions",
                "employee_last_name": f"Route {frappe.generate_hash(length=5)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user_email,
                "organization": self.organization,
                "date_of_joining": nowdate(),
                "employment_status": "Active",
                "user_id": user_email,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", employee.name))
        return employee

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
        if applicant_user:
            applicant.db_set("applicant_user", applicant_user, update_modified=False)
        applicant.reload()
        self._created.append(("Student Applicant", applicant.name))
        return applicant

    def _create_guardian(self, user_email: str):
        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": "Family",
                "guardian_last_name": "Route",
                "guardian_email": user_email,
                "guardian_mobile_phone": "+14155550131",
                "user": user_email,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Guardian", guardian.name))
        return guardian

    def _set_admissions_access_mode(self, value: str):
        frappe.db.set_single_value("Admission Settings", "admissions_access_mode", value)

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
