# ifitwala_ed/admission/doctype/inquiry/test_inquiry.py
# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.admission_utils import (
    _school_belongs_to_organization_scope,
    _validate_admissions_assignee,
    from_inquiry_invite,
)
from ifitwala_ed.tests.factories.users import make_user


class TestInquiry(FrappeTestCase):
    def test_insert_legacy_new_inquiry_state_is_rejected(self):
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Legacy",
                "workflow_state": "New Inquiry",
            }
        )
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def _ensure_role(self, user: str, role: str) -> None:
        if not frappe.db.exists("Role", role):
            self.skipTest(f"Missing Role '{role}' in this site.")
        if frappe.db.exists("Has Role", {"parent": user, "role": role}):
            return
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parent": user,
                "parenttype": "User",
                "parentfield": "roles",
                "role": role,
            }
        ).insert(ignore_permissions=True)

    def test_validate_admissions_assignee_allows_manager_or_officer(self):
        manager = make_user()
        self._ensure_role(manager.name, "Admission Manager")
        _validate_admissions_assignee(manager.name)

        officer = make_user()
        self._ensure_role(officer.name, "Admission Officer")
        _validate_admissions_assignee(officer.name)

    def test_validate_admissions_assignee_rejects_disabled_or_no_role(self):
        no_role = make_user()
        with self.assertRaises(frappe.ValidationError):
            _validate_admissions_assignee(no_role.name)

        disabled = make_user()
        self._ensure_role(disabled.name, "Admission Officer")
        frappe.db.set_value("User", disabled.name, "enabled", 0)
        with self.assertRaises(frappe.ValidationError):
            _validate_admissions_assignee(disabled.name)

    def test_school_belongs_to_organization_scope_respects_nestedset(self):
        parent_org = self._make_organization("Org Parent", is_group=1)
        child_org = self._make_organization("Org Child", parent=parent_org)
        sibling_org = self._make_organization("Org Sibling", parent=parent_org)
        school = self._make_school(child_org, "Scope School")

        self.assertTrue(_school_belongs_to_organization_scope(school, child_org))
        self.assertTrue(_school_belongs_to_organization_scope(school, parent_org))
        self.assertFalse(_school_belongs_to_organization_scope(school, sibling_org))

    def test_from_inquiry_invite_rejects_mismatched_school_organization(self):
        parent_org = self._make_organization("Invite Parent", is_group=1)
        child_org = self._make_organization("Invite Child", parent=parent_org)
        sibling_org = self._make_organization("Invite Sibling", parent=parent_org)
        school = self._make_school(child_org, "Invite School")
        inquiry = self._make_inquiry()

        with patch("ifitwala_ed.admission.admission_utils.ensure_admissions_permission", return_value="Administrator"):
            with self.assertRaises(frappe.ValidationError):
                from_inquiry_invite(
                    inquiry_name=inquiry.name,
                    school=school,
                    organization=sibling_org,
                )

    def test_from_inquiry_invite_handles_inquiry_without_middle_name_field(self):
        parent_org = self._make_organization("Invite Root", is_group=1)
        child_org = self._make_organization("Invite Child Ok", parent=parent_org)
        school = self._make_school(child_org, "Invite School Ok")
        inquiry_email = f"inquiry-{frappe.generate_hash(length=8)}@example.com"
        inquiry = self._make_inquiry(email=inquiry_email)

        with patch("ifitwala_ed.admission.admission_utils.ensure_admissions_permission", return_value="Administrator"):
            applicant_name = from_inquiry_invite(
                inquiry_name=inquiry.name,
                school=school,
                organization=parent_org,
            )

        self.assertTrue(applicant_name)
        linked = frappe.db.get_value(
            "Student Applicant",
            applicant_name,
            ["inquiry", "school", "organization", "applicant_contact", "applicant_email"],
            as_dict=True,
        )
        self.assertEqual(linked.inquiry, inquiry.name)
        self.assertEqual(linked.school, school)
        self.assertEqual(linked.organization, parent_org)
        self.assertTrue(bool(linked.applicant_contact))
        self.assertEqual(linked.applicant_email, inquiry_email)
        self.assertEqual(frappe.db.get_value("Inquiry", inquiry.name, "contact"), linked.applicant_contact)
        self.assertTrue(
            bool(
                frappe.db.exists(
                    "Dynamic Link",
                    {
                        "parenttype": "Contact",
                        "parentfield": "links",
                        "parent": linked.applicant_contact,
                        "link_doctype": "Student Applicant",
                        "link_name": applicant_name,
                    },
                )
            )
        )

    def test_from_inquiry_invite_repairs_existing_applicant_contact_link(self):
        parent_org = self._make_organization("Repair Root", is_group=1)
        child_org = self._make_organization("Repair Child", parent=parent_org)
        school = self._make_school(child_org, "Repair School")
        inquiry = self._make_inquiry(email=f"repair-{frappe.generate_hash(length=8)}@example.com")

        with patch("ifitwala_ed.admission.admission_utils.ensure_admissions_permission", return_value="Administrator"):
            applicant_name = from_inquiry_invite(
                inquiry_name=inquiry.name,
                school=school,
                organization=parent_org,
            )

        applicant = frappe.get_doc("Student Applicant", applicant_name)
        self.assertTrue(bool(applicant.applicant_contact))
        dynamic_link_name = frappe.db.get_value(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "parent": applicant.applicant_contact,
                "link_doctype": "Student Applicant",
                "link_name": applicant_name,
            },
            "name",
        )
        if dynamic_link_name:
            frappe.delete_doc("Dynamic Link", dynamic_link_name, force=1, ignore_permissions=True)

        with patch("ifitwala_ed.admission.admission_utils.ensure_admissions_permission", return_value="Administrator"):
            existing_name = from_inquiry_invite(
                inquiry_name=inquiry.name,
                school=school,
                organization=parent_org,
            )

        self.assertEqual(existing_name, applicant_name)
        self.assertTrue(
            bool(
                frappe.db.exists(
                    "Dynamic Link",
                    {
                        "parenttype": "Contact",
                        "parentfield": "links",
                        "parent": applicant.applicant_contact,
                        "link_doctype": "Student Applicant",
                        "link_name": applicant_name,
                    },
                )
            )
        )

    def _make_organization(self, prefix: str, parent: str | None = None, is_group: int = 0) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"ORG{frappe.generate_hash(length=4)}",
                "is_group": is_group,
                "parent_organization": parent,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_school(self, organization: str, prefix: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_inquiry(self, *, email: str | None = None):
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Invite",
                "last_name": "Check",
                "email": email,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc
