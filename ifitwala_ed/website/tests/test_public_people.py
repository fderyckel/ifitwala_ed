from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website import public_people


class TestPublicPeopleService(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        public_people.invalidate_public_people_cache()

    def tearDown(self):
        public_people.invalidate_public_people_cache()

    def test_public_people_reads_employee_and_designation_fields(self):
        organization = make_organization(prefix="Public People Org")
        school = make_school(organization.name, prefix="Public People School")
        designation = _make_designation(
            organization=organization.name,
            school=school.name,
            title="Teacher",
            role_profile="Academic Staff",
        )
        _make_employee(
            school=school.name,
            organization=organization.name,
            designation=designation.name,
            first_name="Amina",
        )

        with patch(
            "ifitwala_ed.website.public_people.build_employee_image_variants",
            return_value={"original": None, "card": None, "medium": None, "thumb": None},
        ):
            rows = public_people.get_public_people_records(
                school_names=(school.name,),
                organization_name=organization.name,
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Amina Public")
        self.assertEqual(rows[0]["title"], designation.designation_name)
        self.assertEqual(rows[0]["bio"], "Amina supports the school community.")
        self.assertEqual(rows[0]["role_profile"], "Academic Staff")
        self.assertIsNone(rows[0]["public_email"])
        self.assertIsNone(rows[0]["public_phone"])
        self.assertIsNone(rows[0]["sort_order"])

    def test_public_people_hides_employees_without_show_on_website(self):
        organization = make_organization(prefix="Public People Draft Org")
        school = make_school(organization.name, prefix="Public People Draft School")
        designation = _make_designation(
            organization=organization.name,
            school=school.name,
            title="Counselor",
            role_profile="Counselor",
        )
        _make_employee(
            school=school.name,
            organization=organization.name,
            designation=designation.name,
            first_name="Bianca",
            show_on_website=0,
        )

        with patch(
            "ifitwala_ed.website.public_people.build_employee_image_variants",
            return_value={"original": None, "card": None, "medium": None, "thumb": None},
        ):
            rows = public_people.get_public_people_records(
                school_names=(school.name,),
                organization_name=organization.name,
            )

        self.assertEqual(rows, [])

    def test_public_people_supports_optional_profile_pages_from_employee_fields(self):
        organization = make_organization(prefix="Public Profile Org")
        school = make_school(organization.name, prefix="Public Profile School")
        school.website_slug = f"profile-{frappe.generate_hash(length=6)}"
        school.is_published = 1
        school.save(ignore_permissions=True)

        designation = _make_designation(
            organization=organization.name,
            school=school.name,
            title="Teacher",
            role_profile="Academic Staff",
        )
        employee = _make_employee(
            school=school.name,
            organization=organization.name,
            designation=designation.name,
            first_name="Chloe",
        )
        employee.show_public_profile_page = 1
        employee.featured_on_website = 1
        employee.website_sort_order = 3
        employee.bio = "Chloe leads interdisciplinary learning and advisory support."
        employee.save(ignore_permissions=True)

        with patch(
            "ifitwala_ed.website.public_people.build_employee_image_variants",
            return_value={"original": None, "card": None, "medium": None, "thumb": None},
        ):
            rows = public_people.get_public_people_records(
                school_names=(school.name,),
                organization_name=organization.name,
            )
            person = public_people.get_public_person_by_slug(
                school_name=school.name,
                organization_name=organization.name,
                profile_slug=employee.public_profile_slug,
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["profile_slug"], employee.public_profile_slug)
        self.assertTrue(rows[0]["has_profile_page"])
        self.assertEqual(
            rows[0]["profile_url"], f"/schools/{school.website_slug}/people/{employee.public_profile_slug}"
        )
        self.assertTrue(rows[0]["featured"])
        self.assertEqual(rows[0]["sort_order"], 3)
        self.assertEqual(person["employee"], employee.name)
        self.assertEqual(person["full_bio"], employee.bio)


def _make_designation(*, organization: str, school: str | None, title: str, role_profile: str):
    designation = frappe.get_doc(
        {
            "doctype": "Designation",
            "designation_name": f"{title} {frappe.generate_hash(length=6)}",
            "organization": organization,
            "school": school,
            "default_role_profile": role_profile,
        }
    )
    designation.insert()
    return designation


def _make_employee(
    *,
    school: str,
    organization: str,
    designation: str,
    first_name: str,
    show_on_website: int = 1,
):
    employee = frappe.get_doc(
        {
            "doctype": "Employee",
            "employee_first_name": first_name,
            "employee_last_name": "Public",
            "employee_gender": "Female",
            "employee_professional_email": f"{first_name.lower()}.{frappe.generate_hash(length=6)}@example.com",
            "date_of_joining": "2025-01-01",
            "employment_status": "Active",
            "organization": organization,
            "school": school,
            "designation": designation,
            "show_on_website": show_on_website,
            "small_bio": f"{first_name} supports the school community.",
        }
    )
    employee.insert()
    return employee
