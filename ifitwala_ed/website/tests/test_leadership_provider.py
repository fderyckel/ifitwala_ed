from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website.providers import leadership as provider


class TestLeadershipProvider(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        provider.invalidate_leadership_cache()

    def tearDown(self):
        provider.invalidate_leadership_cache()

    def test_groups_visible_staff_into_academic_leadership_and_staff_sections(self):
        organization = make_organization(prefix="Leadership Org")
        school = make_school(organization.name, prefix="Leadership School")

        _ensure_role("Academic Admin")
        _ensure_role("Academic Staff")

        principal = _make_designation(
            organization=organization.name,
            school=school.name,
            title="Principal",
            role_profile="Academic Admin",
        )
        teacher = _make_designation(
            organization=organization.name,
            school=school.name,
            title="Teacher",
            role_profile="Academic Staff",
        )
        registrar = _make_designation(
            organization=organization.name,
            school=None,
            title="Registrar",
            role_profile="Employee",
        )

        _make_employee(
            school=school.name, organization=organization.name, designation=principal.name, first_name="Amina"
        )
        _make_employee(
            school=school.name, organization=organization.name, designation=teacher.name, first_name="Benoit"
        )
        _make_employee(
            school=school.name, organization=organization.name, designation=registrar.name, first_name="Clara"
        )
        _make_employee(
            school=school.name,
            organization=organization.name,
            designation=teacher.name,
            first_name="Hidden",
            show_on_website=0,
        )

        with patch(
            "ifitwala_ed.website.providers.leadership.build_employee_image_variants",
            return_value={"original": None, "card": None},
        ):
            payload = provider.get_context(
                school=frappe.get_doc("School", school.name),
                page=frappe._dict(),
                block_props={
                    "title": "Leadership & Administration",
                    "limit": 4,
                    "staff_limit": 4,
                    "show_staff_carousel": True,
                    "role_profiles": ["Academic Admin"],
                },
            )

        sections = payload["data"]["sections"]
        self.assertEqual([section["key"] for section in sections], ["leadership", "staff"])
        self.assertEqual([person["name"] for person in sections[0]["people"]], ["Amina Leadership"])
        self.assertEqual(
            [person["name"] for person in sections[1]["people"]],
            ["Clara Leadership", "Benoit Leadership"],
        )

    def test_manual_designation_roles_override_default_role_profile_grouping(self):
        organization = make_organization(prefix="Leadership Override Org")
        school = make_school(organization.name, prefix="Leadership Override School")

        _ensure_role("Academic Admin")

        principal = _make_designation(
            organization=organization.name,
            school=school.name,
            title="Principal",
            role_profile="Academic Admin",
        )
        dean = _make_designation(
            organization=organization.name,
            school=school.name,
            title="Dean",
            role_profile="Employee",
        )
        teacher = _make_designation(
            organization=organization.name,
            school=school.name,
            title="Teacher",
            role_profile="Employee",
        )

        _make_employee(school=school.name, organization=organization.name, designation=principal.name, first_name="Ari")
        _make_employee(school=school.name, organization=organization.name, designation=dean.name, first_name="Bianca")
        _make_employee(school=school.name, organization=organization.name, designation=teacher.name, first_name="Cleo")

        with patch(
            "ifitwala_ed.website.providers.leadership.build_employee_image_variants",
            return_value={"original": None, "card": None},
        ):
            payload = provider.get_context(
                school=frappe.get_doc("School", school.name),
                page=frappe._dict(),
                block_props={
                    "roles": [dean.name],
                    "limit": 4,
                    "staff_limit": 4,
                    "show_staff_carousel": True,
                    "role_profiles": ["Academic Admin"],
                },
            )

        sections = payload["data"]["sections"]
        self.assertEqual([person["name"] for person in sections[0]["people"]], ["Bianca Leadership"])
        self.assertEqual(
            [person["name"] for person in sections[1]["people"]],
            ["Ari Leadership", "Cleo Leadership"],
        )


def _ensure_role(role_name: str):
    if frappe.db.exists("Role", role_name):
        return
    frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(ignore_permissions=True)


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
            "small_bio": f"{first_name} helps lead the school community.",
        }
    )
    employee.insert(ignore_permissions=True)
    return employee
