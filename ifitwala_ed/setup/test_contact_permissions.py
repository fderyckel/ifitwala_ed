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
    "Assistant Admin": {
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "email": 1,
        "comment": 1,
        "assign": 1,
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


class TestContactPermissions(FrappeTestCase):
    def test_grant_core_crm_permissions_creates_missing_roles_before_docperm_seed(self):
        if frappe.db.exists("Role", "Assistant Admin"):
            frappe.delete_doc("Role", "Assistant Admin", force=1, ignore_permissions=True)

        grant_core_crm_permissions()

        self.assertTrue(frappe.db.exists("Role", "Assistant Admin"))

    def test_grant_core_crm_permissions_seeds_contact_rows_for_editor_roles(self):
        grant_core_crm_permissions()

        rows = frappe.get_all(
            "Custom DocPerm",
            filters={
                "parent": "Contact",
                "permlevel": 0,
                "role": ["in", list(CONTACT_ROLE_MATRIX)],
            },
            fields=["role", "read", "write", "create", "delete", "email", "comment", "assign"],
            limit=len(CONTACT_ROLE_MATRIX),
        )
        by_role = {row.role: row for row in rows}

        self.assertEqual(set(by_role), set(CONTACT_ROLE_MATRIX))

        for role, expected in CONTACT_ROLE_MATRIX.items():
            for fieldname, value in expected.items():
                self.assertEqual(
                    int(by_role[role].get(fieldname) or 0),
                    value,
                    msg=f"Unexpected {fieldname} for role {role}",
                )

    def test_contact_permission_query_conditions_do_not_add_app_scope_filters(self):
        with patch("ifitwala_ed.utilities.contact_utils.frappe.get_roles", return_value=["Academic Admin"]):
            self.assertEqual(contact_utils.contact_permission_query_conditions("academic-admin@example.com"), "")

    def test_contact_has_permission_defers_to_core_permission_handler(self):
        doc = frappe._dict(name="CONTACT-0001")

        with patch("ifitwala_ed.utilities.contact_utils._core_has_permission", return_value=True) as mocked:
            self.assertTrue(contact_utils.contact_has_permission(doc, "write", "staff@example.com"))

        mocked.assert_called_once_with(doc, "write", "staff@example.com")
