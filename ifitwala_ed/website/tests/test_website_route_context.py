# ifitwala_ed/website/tests/test_website_route_context.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website import public_people
from ifitwala_ed.website.renderer import build_render_context
from ifitwala_ed.www.index import get_context as get_index_context
from ifitwala_ed.www.website import get_context


class TestWebsiteRouteContext(FrappeTestCase):
    def setUp(self):
        public_people.invalidate_public_people_cache()

    def tearDown(self):
        public_people.invalidate_public_people_cache()

    def test_school_website_route_uses_renderer_context(self):
        original_request = self._set_request_path("/schools/test/about")
        original_form_dict = self._set_form_dict({"preview": "1"})
        context = frappe._dict()

        try:
            with patch(
                "ifitwala_ed.www.website.build_render_context",
                return_value={
                    "seo": {"meta_title": "Preview"},
                    "template": "ifitwala_ed/website/templates/page.html",
                },
            ) as mocked_build_render_context:
                result = get_context(context)
        finally:
            self._restore_form_dict(original_form_dict)
            self._restore_request(original_request)

        self.assertEqual(result.no_cache, 1)
        self.assertEqual(result.seo["meta_title"], "Preview")
        mocked_build_render_context.assert_called_once_with(
            route="/schools/test/about",
            preview=True,
        )

    def test_root_index_redirects_when_renderer_requests_redirect(self):
        original_request = self._set_request_path("/")
        original_form_dict = self._set_form_dict({})
        original_redirect = getattr(frappe.local.flags, "redirect_location", None)
        context = frappe._dict()
        redirected_to = None

        try:
            frappe.local.flags.redirect_location = None
            with patch(
                "ifitwala_ed.www.index.build_render_context",
                return_value={"redirect_location": "/schools/demo"},
            ):
                with self.assertRaises(frappe.Redirect):
                    get_index_context(context)
            redirected_to = frappe.local.flags.redirect_location
        finally:
            self._restore_form_dict(original_form_dict)
            self._restore_request(original_request)
            frappe.local.flags.redirect_location = original_redirect

        self.assertEqual(redirected_to, "/schools/demo")

    def test_public_person_profile_route_builds_profile_context(self):
        organization = make_organization(prefix="Route Profile Org")
        school = make_school(organization.name, prefix="Route Profile School")
        school.website_slug = f"route-{frappe.generate_hash(length=6)}"
        school.is_published = 1
        school.save(ignore_permissions=True)

        designation = frappe.get_doc(
            {
                "doctype": "Designation",
                "designation_name": f"Teacher {frappe.generate_hash(length=6)}",
                "organization": organization.name,
                "school": school.name,
                "default_role_profile": "Academic Staff",
            }
        ).insert(ignore_permissions=True)

        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Noor",
                "employee_last_name": "Route",
                "employee_gender": "Female",
                "employee_professional_email": f"noor.{frappe.generate_hash(length=6)}@example.com",
                "date_of_joining": "2025-01-01",
                "employment_status": "Active",
                "organization": organization.name,
                "school": school.name,
                "designation": designation.name,
                "show_on_website": 1,
                "show_public_profile_page": 1,
                "small_bio": "Noor coordinates interdisciplinary projects.",
            }
        ).insert(ignore_permissions=True)

        with patch(
            "ifitwala_ed.website.public_people.build_employee_image_variants",
            return_value={"original": None, "card": None, "medium": None, "thumb": None},
        ):
            context = build_render_context(
                route=f"/schools/{school.website_slug}/people/{employee.public_profile_slug}",
                preview=False,
            )

        self.assertEqual(context["template"], "ifitwala_ed/website/templates/person_profile.html")
        self.assertEqual(context["person"]["employee"], employee.name)
        self.assertEqual(context["person"]["profile_slug"], employee.public_profile_slug)

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

    def _set_form_dict(self, payload: dict):
        original = getattr(frappe.local, "form_dict", None)
        frappe.local.form_dict = frappe._dict(payload)
        return original

    def _restore_form_dict(self, original):
        if original is None:
            if hasattr(frappe.local, "form_dict"):
                del frappe.local.form_dict
            return
        frappe.local.form_dict = original
