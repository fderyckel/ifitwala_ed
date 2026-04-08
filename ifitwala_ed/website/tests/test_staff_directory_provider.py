from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website import public_people
from ifitwala_ed.website.providers import staff_directory as provider


class TestStaffDirectoryProvider(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        public_people.invalidate_public_people_cache()

    def tearDown(self):
        public_people.invalidate_public_people_cache()

    def test_directory_is_exact_school_by_default(self):
        organization = make_organization(prefix="Staff Directory Org")
        root_school = make_school(organization.name, prefix="Staff Directory Root", is_group=1)
        child_school = make_school(
            organization.name,
            prefix="Staff Directory Child",
            parent_school=root_school.name,
        )

        teacher = _make_designation(
            organization=organization.name,
            school=None,
            title="Teacher",
            role_profile="Academic Staff",
        )
        _make_employee(
            school=root_school.name,
            organization=organization.name,
            designation=teacher.name,
            first_name="Amina",
        )
        _make_employee(
            school=child_school.name,
            organization=organization.name,
            designation=teacher.name,
            first_name="Bianca",
        )

        with patch(
            "ifitwala_ed.website.public_people.build_employee_image_variants",
            return_value={"original": None, "card": None, "medium": None, "thumb": None},
        ):
            payload = provider.get_context(
                school=frappe.get_doc("School", root_school.name),
                page=frappe._dict(),
                block_props={},
            )

        people = payload["data"]["people"]
        self.assertEqual([person["name"] for person in people], ["Amina Leadership"])
        self.assertEqual(payload["data"]["designation_options"][0]["label"], teacher.designation_name)

    def test_directory_include_filters_use_designation_or_role_profile_union(self):
        organization = make_organization(prefix="Staff Directory Filter Org")
        school = make_school(organization.name, prefix="Staff Directory Filter School")

        teacher = _make_designation(
            organization=organization.name,
            school=None,
            title="Teacher",
            role_profile="Academic Staff",
        )
        counselor = _make_designation(
            organization=organization.name,
            school=None,
            title="Counselor",
            role_profile="Counselor",
        )
        registrar = _make_designation(
            organization=organization.name,
            school=None,
            title="Registrar",
            role_profile="Employee",
        )

        _make_employee(
            school=school.name,
            organization=organization.name,
            designation=teacher.name,
            first_name="Ari",
        )
        _make_employee(
            school=school.name,
            organization=organization.name,
            designation=counselor.name,
            first_name="Clara",
        )
        _make_employee(
            school=school.name,
            organization=organization.name,
            designation=registrar.name,
            first_name="Erin",
        )

        with patch(
            "ifitwala_ed.website.public_people.build_employee_image_variants",
            return_value={"original": None, "card": None, "medium": None, "thumb": None},
        ):
            payload = provider.get_context(
                school=frappe.get_doc("School", school.name),
                page=frappe._dict(),
                block_props={
                    "designations": [teacher.name],
                    "role_profiles": ["Counselor"],
                    "show_role_profile_filter": True,
                },
            )

        people = payload["data"]["people"]
        self.assertEqual([person["name"] for person in people], ["Clara Leadership", "Ari Leadership"])
        self.assertEqual(
            [option["label"] for option in payload["data"]["designation_options"]],
            sorted([counselor.designation_name, teacher.designation_name]),
        )
        self.assertEqual(
            [option["label"] for option in payload["data"]["role_profile_options"]],
            ["Academic Staff", "Counselor"],
        )
        self.assertTrue(payload["data"]["show_role_profile_filter"])


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
    designation.insert(ignore_permissions=True)
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
            "employee_last_name": "Leadership",
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
    employee.insert(ignore_permissions=True)
    return employee
