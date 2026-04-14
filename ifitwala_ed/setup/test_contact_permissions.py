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
        "delete": 1,
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
        ):
            condition = contact_utils.contact_permission_query_conditions("academic.assistant@example.com")

        self.assertIn("SCH-ROOT", condition)
        self.assertIn("SCH-CHILD", condition)
        self.assertIn("NOT", condition)

    def test_contact_permission_query_conditions_scope_employee_contacts_for_academic_org_tree_when_no_school(self):
        with (
            patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.utilities.contact_utils._resolve_academic_contact_school_scope", return_value=[]),
            patch(
                "ifitwala_ed.utilities.contact_utils._resolve_academic_contact_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            condition = contact_utils.contact_permission_query_conditions("academic.admin@example.com")

        self.assertIn("ORG-ROOT", condition)
        self.assertIn("ORG-CHILD", condition)
        self.assertIn("NOT", condition)

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

    def test_contact_has_permission_keeps_core_access_for_non_employee_contact(self):
        doc = frappe._dict(name="CONTACT-0001")

        with (
            patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True) as mocked,
            patch("ifitwala_ed.utilities.contact_utils._employee_contact_scope_matches", return_value=None),
        ):
            self.assertTrue(contact_utils.contact_has_permission(doc, "write", "staff@example.com"))

        mocked.assert_called_once_with(doc, "write", "staff@example.com")
