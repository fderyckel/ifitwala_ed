# ifitwala_ed/setup/test_contact_permissions.py

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.setup import grant_core_crm_permissions
from ifitwala_ed.utilities import contact_utils

CONTACT_ROLE_MATRIX = {
    "Admission Officer": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Admission Manager": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Marketing User": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Marketing Manager": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Academic Admin": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Academic Assistant": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Curriculum Coordinator": {
        "read": 1,
        "write": 0,
        "create": 0,
        "delete": 0,
        "email": 0,
        "comment": 0,
        "assign": 0,
    },
    "HR Manager": {
        "read": 1,
        "write": 0,
        "create": 0,
        "delete": 0,
        "email": 0,
        "comment": 0,
        "assign": 0,
    },
    "HR User": {
        "read": 1,
        "write": 0,
        "create": 0,
        "delete": 0,
        "email": 0,
        "comment": 0,
        "assign": 0,
    },
    "Employee": {
        "read": 1,
        "write": 0,
        "create": 0,
        "delete": 0,
        "email": 0,
        "comment": 0,
        "assign": 0,
    },
    "Accounts User": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Accounts Manager": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
}

ADDRESS_ROLE_MATRIX = {
    "Admission Officer": {
        "read": 1,
        "write": 0,
        "create": 0,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Admission Manager": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Marketing User": {
        "read": 1,
        "write": 0,
        "create": 0,
        "delete": 0,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Marketing Manager": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Academic Admin": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Academic Assistant": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "email": 1,
        "comment": 1,
        "assign": 1,
    },
    "Curriculum Coordinator": {
        "read": 1,
        "write": 0,
        "create": 0,
        "delete": 0,
        "email": 0,
        "comment": 0,
        "assign": 0,
    },
}


class TestContactPermissions(FrappeTestCase):
    @staticmethod
    def _available_permission_fields() -> list[str]:
        candidate_fields = ["role", "read", "write", "create", "delete", "email", "comment", "assign"]
        return [fieldname for fieldname in candidate_fields if frappe.db.has_column("Custom DocPerm", fieldname)]

    def test_grant_core_crm_permissions_creates_missing_roles_before_docperm_seed(self):
        if frappe.db.exists("Role", "Academic Assistant"):
            frappe.delete_doc("Role", "Academic Assistant", force=1, ignore_permissions=True)

        grant_core_crm_permissions()

        self.assertTrue(frappe.db.exists("Role", "Academic Assistant"))

    def test_grant_core_crm_permissions_seeds_contact_rows_for_editor_roles(self):
        grant_core_crm_permissions()

        available_fields = self._available_permission_fields()
        rows = frappe.get_all(
            "Custom DocPerm",
            filters={
                "parent": "Contact",
                "permlevel": 0,
                "role": ["in", list(CONTACT_ROLE_MATRIX)],
            },
            fields=available_fields,
            limit=len(CONTACT_ROLE_MATRIX),
        )
        by_role = {row.role: row for row in rows}

        self.assertEqual(set(by_role), set(CONTACT_ROLE_MATRIX))

        for role, expected in CONTACT_ROLE_MATRIX.items():
            for fieldname, value in expected.items():
                if fieldname not in available_fields:
                    continue
                self.assertEqual(
                    int(by_role[role].get(fieldname) or 0),
                    value,
                    msg=f"Unexpected {fieldname} for role {role}",
                )

    def test_grant_core_crm_permissions_seeds_address_rows_for_canonical_roles(self):
        grant_core_crm_permissions()

        available_fields = self._available_permission_fields()
        rows = frappe.get_all(
            "Custom DocPerm",
            filters={
                "parent": "Address",
                "permlevel": 0,
                "role": ["in", list(ADDRESS_ROLE_MATRIX)],
            },
            fields=available_fields,
            limit=len(ADDRESS_ROLE_MATRIX),
        )
        by_role = {row.role: row for row in rows}

        self.assertEqual(set(by_role), set(ADDRESS_ROLE_MATRIX))

        for role, expected in ADDRESS_ROLE_MATRIX.items():
            for fieldname, value in expected.items():
                if fieldname not in available_fields:
                    continue
                self.assertEqual(
                    int(by_role[role].get(fieldname) or 0),
                    value,
                    msg=f"Unexpected Address {fieldname} for role {role}",
                )

    def test_contact_permission_query_conditions_scope_employee_contacts_for_hr(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["HR User"]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_hr_contact_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            condition = contact_utils.contact_permission_query_conditions("hr.user@example.com")

        self.assertIn("tabDynamic Link", condition)
        self.assertIn("tabEmployee", condition)
        self.assertIn("ORG-ROOT", condition)
        self.assertIn("ORG-CHILD", condition)

    def test_contact_permission_query_conditions_scope_employee_contacts_for_academic_school_tree(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Assistant"]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_academic_contact_school_scope",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
            patch("ifitwala_ed.utilities.contact_utils._resolve_education_contact_school_scope", return_value=[]),
        ):
            condition = contact_utils.contact_permission_query_conditions("academic.assistant@example.com")

        self.assertIn("SCH-ROOT", condition)
        self.assertIn("SCH-CHILD", condition)
        self.assertNotEqual(condition, "1=0")

    def test_contact_permission_query_conditions_scope_employee_contacts_for_academic_org_tree_when_no_school(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.utilities.contact_utils._resolve_academic_contact_school_scope", return_value=[]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_academic_contact_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch("ifitwala_ed.utilities.contact_utils._resolve_education_contact_school_scope", return_value=[]),
        ):
            condition = contact_utils.contact_permission_query_conditions("academic.admin@example.com")

        self.assertIn("ORG-ROOT", condition)
        self.assertIn("ORG-CHILD", condition)
        self.assertNotEqual(condition, "1=0")

    def test_contact_permission_query_conditions_scope_admissions_and_marketing_contacts(self):
        for role in ("Admission Officer", "Admission Manager", "Marketing User", "Marketing Manager"):
            with (
                patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=[role]),
                patch(
                    "ifitwala_ed.utilities.contact_utils._resolve_education_contact_school_scope",
                    return_value=["SCH-ROOT", "SCH-CHILD"],
                ),
                patch(
                    "ifitwala_ed.utilities.contact_utils._resolve_education_contact_org_scope",
                    return_value=["ORG-ROOT", "ORG-CHILD"],
                ),
            ):
                condition = contact_utils.contact_permission_query_conditions(f"{frappe.scrub(role)}@example.com")

            self.assertIn("Inquiry", condition, msg=f"Expected scoped Inquiry Contact condition for {role}")
            self.assertIn("Student Applicant", condition, msg=f"Expected scoped applicant Contact condition for {role}")
            self.assertIn("Guardian", condition, msg=f"Expected scoped guardian Contact condition for {role}")
            self.assertIn("SCH-ROOT", condition, msg=f"Expected school scope for {role}")
            self.assertNotEqual(condition, "", msg=f"Expected Contact query scope for {role}")

    def test_contact_permission_query_conditions_deny_unscoped_system_manager_contact_list(self):
        with patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["System Manager"]):
            condition = contact_utils.contact_permission_query_conditions("system.manager@example.com")

        self.assertEqual(condition, "1=0")

    def test_contact_permission_query_conditions_deny_roles_without_contact_scope(self):
        for role in ("Accounts User", "Accounts Manager", "Curriculum Coordinator"):
            with patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=[role]):
                condition = contact_utils.contact_permission_query_conditions(f"{frappe.scrub(role)}@example.com")

            self.assertEqual(condition, "1=0", msg=f"Expected no native Contact list for {role}")

    def test_contact_permission_query_conditions_scope_student_applicant_contacts_for_academic_staff(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Assistant"]),
            patch("ifitwala_ed.utilities.contact_utils._resolve_academic_contact_school_scope", return_value=[]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_education_contact_school_scope",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_education_contact_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            condition = contact_utils.contact_permission_query_conditions("academic.assistant@example.com")

        self.assertIn("Inquiry", condition)
        self.assertIn("contact = `tabContact`.name", condition)
        self.assertIn("Student Applicant", condition)
        self.assertIn("applicant_contact", condition)
        self.assertIn("Student", condition)
        self.assertIn("Guardian", condition)
        self.assertIn("ORG-ROOT", condition)
        self.assertIn("ORG-CHILD", condition)
        self.assertIn("SCH-ROOT", condition)
        self.assertIn("SCH-CHILD", condition)
        self.assertNotEqual(condition, "1=0")

    def test_education_contact_scope_matches_scoped_student_applicant_for_academic_staff(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Assistant"]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_education_contact_school_scope",
                return_value=["SCH-CHILD"],
            ),
            patch("ifitwala_ed.utilities.contact_utils._resolve_education_contact_org_scope", return_value=[]),
            patch(
                "ifitwala_ed.utilities.contact_utils.frappe.get_all",
                side_effect=[
                    [frappe._dict(link_doctype="Student Applicant", link_name="APP-0001")],
                    [frappe._dict(name="APP-0001", school="SCH-CHILD", student=None)],
                ],
            ),
        ):
            self.assertTrue(
                contact_utils._education_contact_scope_matches(
                    "CONTACT-0001",
                    "academic.assistant@example.com",
                )
            )

    def test_education_contact_scope_matches_reverse_inquiry_contact_for_academic_staff(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Assistant"]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_education_contact_school_scope",
                return_value=["SCH-CHILD"],
            ),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_education_contact_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.utilities.contact_utils.frappe.get_all",
                side_effect=[
                    [],
                    [frappe._dict(name="INQ-0001", organization="ORG-CHILD", school="", student_applicant="")],
                ],
            ),
        ):
            self.assertTrue(
                contact_utils._education_contact_scope_matches(
                    "Marcus Vance-INQ-26-03-24-002",
                    "academic.assistant@example.com",
                )
            )

    def test_education_contact_scope_matches_reverse_student_applicant_contact_for_academic_staff(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Assistant"]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_education_contact_school_scope",
                return_value=["SCH-CHILD"],
            ),
            patch("ifitwala_ed.utilities.contact_utils._resolve_education_contact_org_scope", return_value=[]),
            patch(
                "ifitwala_ed.utilities.contact_utils.frappe.get_all",
                side_effect=[
                    [],
                    [],
                    [frappe._dict(name="APP-0001", school="SCH-CHILD", student=None)],
                ],
            ),
        ):
            self.assertTrue(
                contact_utils._education_contact_scope_matches(
                    "CONTACT-0001",
                    "academic.assistant@example.com",
                )
            )

    def test_contact_has_permission_allows_scoped_admissions_and_marketing_read_when_core_denies(self):
        doc = frappe._dict(name="CONTACT-0001")

        for role in ("Admission Officer", "Admission Manager", "Marketing User", "Marketing Manager"):
            with (
                patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=False),
                patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=[role]),
                patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=True),
                patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
            ):
                self.assertTrue(
                    contact_utils.contact_has_permission(doc, "read", f"{frappe.scrub(role)}@example.com"),
                    msg=f"Expected scoped Contact read for {role}",
                )

    def test_contact_has_permission_blocks_unscoped_admissions_and_marketing_read(self):
        doc = frappe._dict(name="CONTACT-0001")

        for role in ("Admission Officer", "Admission Manager", "Marketing User", "Marketing Manager"):
            with (
                patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
                patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=[role]),
                patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=None),
                patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
            ):
                self.assertFalse(
                    contact_utils.contact_has_permission(doc, "read", f"{frappe.scrub(role)}@example.com"),
                    msg=f"Expected unscoped Contact read to be blocked for {role}",
                )

    def test_contact_has_permission_blocks_delete_for_ordinary_contact_roles(self):
        doc = frappe._dict(name="CONTACT-0001")

        for role in ("Admission Manager", "Marketing Manager", "Academic Assistant", "Accounts Manager"):
            with (
                patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
                patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=[role]),
            ):
                self.assertFalse(
                    contact_utils.contact_has_permission(doc, "delete", f"{frappe.scrub(role)}@example.com"),
                    msg=f"Expected Contact delete to be blocked for {role}",
                )

    def test_contact_has_permission_blocks_system_manager_unscoped_contact_read(self):
        doc = frappe._dict(name="CONTACT-0001")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["System Manager"]),
            patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=None),
            patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
        ):
            self.assertFalse(contact_utils.contact_has_permission(doc, "read", "system.manager@example.com"))

    def test_contact_has_permission_blocks_unscoped_export_for_ordinary_contact_roles(self):
        doc = frappe._dict(name="CONTACT-0001")

        for role in ("Admission Officer", "Marketing User", "Academic Admin", "Accounts Manager", "System Manager"):
            with (
                patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
                patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=[role]),
                patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=None),
                patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
            ):
                self.assertFalse(
                    contact_utils.contact_has_permission(doc, "export", f"{frappe.scrub(role)}@example.com"),
                    msg=f"Expected unscoped Contact export to be blocked for {role}",
                )

    def test_contact_has_permission_blocks_scoped_export_for_ordinary_contact_roles(self):
        doc = frappe._dict(name="CONTACT-0001")

        for role in ("Admission Officer", "Marketing User", "Academic Admin"):
            with (
                patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
                patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=[role]),
                patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=True),
                patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
            ):
                self.assertFalse(
                    contact_utils.contact_has_permission(doc, "export", f"{frappe.scrub(role)}@example.com"),
                    msg=f"Expected scoped Contact export to be blocked for {role}",
                )

    def test_contact_has_permission_allows_scoped_student_applicant_contact_when_core_denies(self):
        doc = frappe._dict(name="CONTACT-0001")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=False),
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Assistant"]),
            patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=True),
            patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
        ):
            self.assertTrue(contact_utils.contact_has_permission(doc, "read", "academic.assistant@example.com"))

    def test_contact_has_permission_blocks_out_of_scope_student_applicant_contact_for_academic_staff(self):
        doc = frappe._dict(name="CONTACT-0001")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Assistant"]),
            patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=False),
        ):
            self.assertFalse(contact_utils.contact_has_permission(doc, "read", "academic.assistant@example.com"))

    def test_contact_has_permission_blocks_out_of_scope_contact_for_admissions_staff(self):
        doc = frappe._dict(name="CONTACT-0001")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Admission Officer"]),
            patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=False),
        ):
            self.assertFalse(contact_utils.contact_has_permission(doc, "read", "admission.officer@example.com"))

    def test_contact_has_permission_blocks_teacher_style_hostile_contact_id_swap(self):
        doc = frappe._dict(name="CONTACT-GUARDIAN-OUT-OF-SCOPE")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Instructor"]),
            patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=None),
            patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
        ):
            self.assertFalse(contact_utils.contact_has_permission(doc, "read", "instructor@example.com"))

    def test_employee_contact_scope_matches_academic_org_tree_when_no_school(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.utilities.contact_utils._resolve_academic_contact_school_scope", return_value=[]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_academic_contact_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.utilities.contact_utils.frappe.get_all",
                side_effect=[
                    ["EMP-0001"],
                    [frappe._dict(organization="ORG-CHILD")],
                ],
            ),
        ):
            self.assertTrue(contact_utils._employee_contact_scope_matches("CONTACT-0001", "academic.admin@example.com"))

    def test_contact_permission_query_conditions_scope_employee_only_for_employee_role(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Employee"]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_self_employee_contact",
                return_value="EMP-0001",
            ),
        ):
            condition = contact_utils.contact_permission_query_conditions("employee.user@example.com")

        self.assertIn("EMP-0001", condition)
        self.assertNotIn("NOT EXISTS", condition)

    def test_contact_has_permission_blocks_out_of_scope_employee_contact(self):
        doc = frappe._dict(name="CONTACT-0001")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Employee"]),
            patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=False),
        ):
            self.assertFalse(contact_utils.contact_has_permission(doc, "read", "staff@example.com"))

    def test_contact_has_permission_blocks_non_employee_contact_for_employee_role(self):
        doc = frappe._dict(name="CONTACT-0001")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True),
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Employee"]),
            patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=False),
        ):
            self.assertFalse(contact_utils.contact_has_permission(doc, "read", "employee.user@example.com"))

    def test_contact_has_permission_blocks_core_access_for_unscoped_contact(self):
        doc = frappe._dict(name="CONTACT-0001")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True) as mocked,
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Some Other Role"]),
            patch("ifitwala_ed.utilities.contact_utils._education_contact_scope_matches", return_value=None),
            patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
        ):
            self.assertFalse(contact_utils.contact_has_permission(doc, "write", "staff@example.com"))

        mocked.assert_not_called()
