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
from ifitwala_ed.admission.doctype.inquiry.inquiry import _normalize_inquiry_state
from ifitwala_ed.tests.factories.users import make_user


class TestInquiry(FrappeTestCase):
    def test_normalize_legacy_new_inquiry_state(self):
        self.assertEqual(_normalize_inquiry_state("New Inquiry"), "New")

    def test_insert_legacy_new_inquiry_state_is_canonicalized(self):
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Legacy",
                "workflow_state": "New Inquiry",
            }
        )
        doc.insert(ignore_permissions=True)

        self.assertEqual(doc.workflow_state, "New")
        self.assertEqual(frappe.db.get_value("Inquiry", doc.name, "workflow_state"), "New")

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
        inquiry = self._make_inquiry()

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
            ["inquiry", "school", "organization"],
            as_dict=True,
        )
        self.assertEqual(linked.inquiry, inquiry.name)
        self.assertEqual(linked.school, school)
        self.assertEqual(linked.organization, parent_org)

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
                "abbr": f"SCH{frappe.generate_hash(length=4)}",
                "organization": organization,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_inquiry(self):
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Invite",
                "last_name": "Check",
            }
        )
        doc.insert(ignore_permissions=True)
        return doc
