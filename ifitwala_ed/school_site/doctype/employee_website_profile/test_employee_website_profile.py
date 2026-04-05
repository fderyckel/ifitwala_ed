# ifitwala_ed/school_site/doctype/employee_website_profile/test_employee_website_profile.py

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_site.doctype.employee_website_profile.employee_website_profile import (
    compute_employee_profile_status,
    normalize_workflow_state,
)
from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestEmployeeWebsiteProfile(FrappeTestCase):
    def test_workflow_state_normalization_rejects_invalid_state(self):
        with self.assertRaises(frappe.ValidationError):
            normalize_workflow_state("Invalid State")

    def test_employee_profile_status_requires_workflow_published(self):
        status = compute_employee_profile_status(
            employee_is_public=True,
            workflow_state="Approved",
        )
        self.assertEqual(status, "Draft")

    def test_employee_profile_status_requires_employee_to_be_public(self):
        status = compute_employee_profile_status(
            employee_is_public=False,
            workflow_state="Published",
        )
        self.assertEqual(status, "Draft")

    def test_profile_syncs_school_from_employee(self):
        organization = make_organization(prefix="Employee Website Profile Org")
        school = make_school(organization.name, prefix="Employee Website Profile School")
        designation = _make_designation(organization=organization.name, school=school.name, title="Teacher")
        employee = _make_employee(
            school=school.name,
            organization=organization.name,
            designation=designation.name,
            first_name="Amina",
        )

        profile = frappe.get_doc(
            {
                "doctype": "Employee Website Profile",
                "employee": employee.name,
                "workflow_state": "Draft",
                "display_name_override": "Amina Profile",
            }
        ).insert()

        self.assertEqual(profile.school, school.name)
        self.assertEqual(profile.status, "Draft")

    def test_profile_rejects_cross_school_employee_scope(self):
        organization = make_organization(prefix="Employee Website Profile Cross Org")
        school = make_school(organization.name, prefix="Employee Website Profile Base")
        other_school = make_school(organization.name, prefix="Employee Website Profile Other")
        designation = _make_designation(organization=organization.name, school=school.name, title="Teacher")
        employee = _make_employee(
            school=school.name,
            organization=organization.name,
            designation=designation.name,
            first_name="Bianca",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Employee Website Profile",
                    "school": other_school.name,
                    "employee": employee.name,
                    "workflow_state": "Draft",
                }
            ).insert()


def _make_designation(*, organization: str, school: str | None, title: str):
    designation = frappe.get_doc(
        {
            "doctype": "Designation",
            "designation_name": f"{title} {frappe.generate_hash(length=6)}",
            "organization": organization,
            "school": school,
            "default_role_profile": "Academic Staff",
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
            "employee_last_name": "Profile",
            "employee_gender": "Female",
            "employee_professional_email": f"{first_name.lower()}.{frappe.generate_hash(length=6)}@example.com",
            "date_of_joining": "2025-01-01",
            "employment_status": "Active",
            "organization": organization,
            "school": school,
            "designation": designation,
            "show_on_website": show_on_website,
            "small_bio": f"{first_name} supports the school website.",
        }
    )
    employee.insert()
    return employee
