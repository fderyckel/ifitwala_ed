# ifitwala_ed/admission/doctype/inquiry/test_inquiry.py
# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.admission_utils import (
    _school_belongs_to_organization_scope,
    _validate_admissions_assignee,
    _validate_inquiry_assignee_scope,
    from_inquiry_invite,
    get_inquiry_assignees,
)
from ifitwala_ed.tests.factories.users import make_user


class TestInquiry(FrappeTestCase):
    def test_inquiry_lookup_fields_and_lead_fields_are_configured(self):
        meta = frappe.get_meta("Inquiry")

        self.assertEqual(meta.get_field("email").search_index, 1)
        self.assertEqual(meta.get_field("phone_number").search_index, 1)
        self.assertEqual(meta.get_field("source").fieldtype, "Select")
        self.assertEqual(meta.get_field("next_action_note").fieldtype, "Small Text")
        self.assertIn("WhatsApp", meta.get_field("source").options)
        self.assertIn("Line", meta.get_field("source").options)
        self.assertIn("Facebook", meta.get_field("source").options)

    def test_manual_inquiry_can_record_source_and_next_action_note(self):
        doc = self._make_inquiry(
            source="WhatsApp",
            next_action_note="Call parent after school tour dates are confirmed.",
        )

        saved = frappe.db.get_value(
            "Inquiry",
            doc.name,
            ["source", "next_action_note"],
            as_dict=True,
        )
        self.assertEqual(saved.source, "WhatsApp")
        self.assertEqual(saved.next_action_note, "Call parent after school tour dates are confirmed.")

    def test_web_form_inquiry_defaults_source_to_website(self):
        previous = getattr(frappe.flags, "in_web_form", None)
        frappe.flags.in_web_form = True
        try:
            doc = frappe.get_doc(
                {
                    "doctype": "Inquiry",
                    "first_name": "Web",
                    "last_name": "Lead",
                    "email": f"web-{frappe.generate_hash(length=8)}@example.com",
                    "type_of_inquiry": "Admission",
                    "message": "We would like to learn more.",
                }
            )
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_web_form = previous

        self.assertEqual(frappe.db.get_value("Inquiry", doc.name, "source"), "Website")

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

    def test_validate_inquiry_assignee_scope_allows_school_ancestors_and_descendants(self):
        organization = self._make_organization("Inquiry Scope Root", is_group=1)
        root_school = self._make_school(organization, "IIS", is_group=1)
        branch_school = self._make_school(organization, "ISS", parent_school=root_school, is_group=1)
        leaf_school = self._make_school(organization, "IHS", parent_school=branch_school)
        sibling_school = self._make_school(organization, "IPS", parent_school=root_school)

        inquiry = self._make_inquiry(organization=organization, school=branch_school)
        parent_assignee = self._make_employee_user(school=root_school)
        child_assignee = self._make_employee_user(school=leaf_school)
        organization_assignee = self._make_employee_user(organization=organization)
        sibling_assignee = self._make_employee_user(school=sibling_school)

        _validate_inquiry_assignee_scope(parent_assignee.name, inquiry)
        _validate_inquiry_assignee_scope(child_assignee.name, inquiry)
        _validate_inquiry_assignee_scope(organization_assignee.name, inquiry)
        with self.assertRaises(frappe.ValidationError):
            _validate_inquiry_assignee_scope(sibling_assignee.name, inquiry)

    def test_validate_inquiry_assignee_scope_allows_organization_ancestors_and_descendants(self):
        parent_org = self._make_organization("Inquiry Org Parent", is_group=1)
        child_org = self._make_organization("Inquiry Org Child", parent=parent_org, is_group=1)
        grandchild_org = self._make_organization("Inquiry Org Grandchild", parent=child_org)
        sibling_org = self._make_organization("Inquiry Org Sibling", parent=parent_org)

        parent_school = self._make_school(parent_org, "Org Parent School")
        child_school = self._make_school(child_org, "Org Child School")
        grandchild_school = self._make_school(grandchild_org, "Org Grandchild School")
        sibling_school = self._make_school(sibling_org, "Org Sibling School")

        inquiry = self._make_inquiry(organization=child_org)
        parent_assignee = self._make_employee_user(school=parent_school)
        child_assignee = self._make_employee_user(school=child_school)
        grandchild_assignee = self._make_employee_user(school=grandchild_school)
        sibling_assignee = self._make_employee_user(school=sibling_school)

        _validate_inquiry_assignee_scope(parent_assignee.name, inquiry)
        _validate_inquiry_assignee_scope(child_assignee.name, inquiry)
        _validate_inquiry_assignee_scope(grandchild_assignee.name, inquiry)
        with self.assertRaises(frappe.ValidationError):
            _validate_inquiry_assignee_scope(sibling_assignee.name, inquiry)

    def test_get_inquiry_assignees_includes_school_ancestors_descendants_and_excludes_siblings(self):
        organization = self._make_organization("Inquiry Picker Root", is_group=1)
        root_school = self._make_school(organization, "IIS", is_group=1)
        branch_school = self._make_school(organization, "ISS", parent_school=root_school, is_group=1)
        leaf_school = self._make_school(organization, "IHS", parent_school=branch_school)
        sibling_school = self._make_school(organization, "IPS", parent_school=root_school)

        root_user = self._make_employee_user(school=root_school)
        branch_user = self._make_employee_user(school=branch_school)
        leaf_user = self._make_employee_user(school=leaf_school)
        organization_user = self._make_employee_user(organization=organization)
        sibling_user = self._make_employee_user(school=sibling_school)

        with patch("ifitwala_ed.admission.admission_utils.ensure_admissions_permission", return_value="Administrator"):
            rows = get_inquiry_assignees(filters={"organization": organization, "school": branch_school})

        names = {row[0] for row in rows}
        self.assertIn(root_user.name, names)
        self.assertIn(branch_user.name, names)
        self.assertIn(leaf_user.name, names)
        self.assertIn(organization_user.name, names)
        self.assertNotIn(sibling_user.name, names)

    def test_get_inquiry_assignees_includes_organization_ancestors_descendants_and_excludes_siblings(self):
        parent_org = self._make_organization("Inquiry Picker Org Parent", is_group=1)
        child_org = self._make_organization("Inquiry Picker Org Child", parent=parent_org, is_group=1)
        grandchild_org = self._make_organization("Inquiry Picker Org Grandchild", parent=child_org)
        sibling_org = self._make_organization("Inquiry Picker Org Sibling", parent=parent_org)

        parent_school = self._make_school(parent_org, "Picker Org Parent School")
        child_school = self._make_school(child_org, "Picker Org Child School")
        grandchild_school = self._make_school(grandchild_org, "Picker Org Grandchild School")
        sibling_school = self._make_school(sibling_org, "Picker Org Sibling School")

        parent_user = self._make_employee_user(school=parent_school)
        child_user = self._make_employee_user(school=child_school)
        grandchild_user = self._make_employee_user(school=grandchild_school)
        sibling_user = self._make_employee_user(school=sibling_school)

        with patch("ifitwala_ed.admission.admission_utils.ensure_admissions_permission", return_value="Administrator"):
            rows = get_inquiry_assignees(filters={"organization": child_org})

        names = {row[0] for row in rows}
        self.assertIn(parent_user.name, names)
        self.assertIn(child_user.name, names)
        self.assertIn(grandchild_user.name, names)
        self.assertNotIn(sibling_user.name, names)

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
        self.assertEqual(frappe.db.get_value("Inquiry", inquiry.name, "student_applicant"), applicant_name)
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

        frappe.db.set_value("Inquiry", inquiry.name, "student_applicant", None, update_modified=False)

        with patch("ifitwala_ed.admission.admission_utils.ensure_admissions_permission", return_value="Administrator"):
            existing_name = from_inquiry_invite(
                inquiry_name=inquiry.name,
                school=school,
                organization=parent_org,
            )

        self.assertEqual(existing_name, applicant_name)
        self.assertEqual(frappe.db.get_value("Inquiry", inquiry.name, "student_applicant"), applicant_name)
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

    def test_mark_contacted_complete_todo_keeps_assigned_to(self):
        inquiry = self._make_inquiry()
        assignee = "Administrator"

        inquiry.db_set("workflow_state", "Assigned", update_modified=False)
        inquiry.db_set("assigned_to", assignee, update_modified=False)
        inquiry.db_set("followup_due_on", frappe.utils.nowdate(), update_modified=False)
        inquiry.reload()

        with patch("ifitwala_ed.admission.doctype.inquiry.inquiry.ensure_admissions_permission", return_value=assignee):
            inquiry.mark_contacted(complete_todo=1)

        inquiry.reload()
        self.assertEqual(inquiry.workflow_state, "Contacted")
        self.assertEqual(inquiry.assigned_to, assignee)

    def test_mark_contacted_allows_assigned_non_admissions_user(self):
        inquiry = self._make_inquiry()
        assignee = make_user()

        inquiry.db_set("workflow_state", "Assigned", update_modified=False)
        inquiry.db_set("assigned_to", assignee.name, update_modified=False)
        inquiry.db_set("followup_due_on", frappe.utils.nowdate(), update_modified=False)
        inquiry.reload()

        previous_user = frappe.session.user
        try:
            frappe.set_user(assignee.name)
            inquiry.mark_contacted(complete_todo=0)
        finally:
            frappe.set_user(previous_user)

        inquiry.reload()
        self.assertEqual(inquiry.workflow_state, "Contacted")
        self.assertEqual(inquiry.assigned_to, assignee.name)

    def test_mark_contacted_rejects_unassigned_non_admissions_user(self):
        inquiry = self._make_inquiry()
        assignee = make_user()
        other = make_user()

        inquiry.db_set("workflow_state", "Assigned", update_modified=False)
        inquiry.db_set("assigned_to", assignee.name, update_modified=False)
        inquiry.db_set("followup_due_on", frappe.utils.nowdate(), update_modified=False)
        inquiry.reload()

        previous_user = frappe.session.user
        try:
            frappe.set_user(other.name)
            with self.assertRaises(frappe.PermissionError):
                inquiry.mark_contacted(complete_todo=0)
        finally:
            frappe.set_user(previous_user)

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

    def _make_school(
        self,
        organization: str,
        prefix: str,
        *,
        parent_school: str | None = None,
        is_group: int = 0,
    ) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"S{frappe.generate_hash(length=4)}",
                "organization": organization,
                "parent_school": parent_school,
                "is_group": is_group,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_employee_user(self, *, school: str | None = None, organization: str | None = None):
        resolved_organization = organization or frappe.db.get_value("School", school, "organization")
        if not resolved_organization:
            raise ValueError("organization is required when school is not provided")

        user = make_user()
        frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Inquiry",
                "employee_last_name": f"Assignee-{frappe.generate_hash(length=6)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user.name,
                "organization": resolved_organization,
                "school": school,
                "user_id": user.name,
                "date_of_joining": frappe.utils.nowdate(),
                "employment_status": "Active",
            }
        ).insert(ignore_permissions=True)
        return user

    def _make_inquiry(
        self,
        *,
        email: str | None = None,
        organization: str | None = None,
        school: str | None = None,
        source: str | None = None,
        next_action_note: str | None = None,
    ):
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Invite",
                "last_name": "Check",
                "email": email,
                "organization": organization,
                "school": school,
                "source": source,
                "next_action_note": next_action_note,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc
