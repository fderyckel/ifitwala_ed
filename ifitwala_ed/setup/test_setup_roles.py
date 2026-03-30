# ifitwala_ed/setup/test_setup_roles.py

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.initial_setup import complete_initial_setup
from ifitwala_ed.setup.setup import (
    create_designations,
    create_roles_with_homepage,
    ensure_canonical_role_records,
    grant_role_read_select_to_hr,
)


class _DummyDoc:
    def __init__(self, name):
        self.name = name
        self.app_logo = None
        self.ifitwala_initial_setup = 0

    def insert(self, ignore_permissions=True):
        return self

    def save(self, ignore_permissions=True):
        return self


class TestSetupRoles(FrappeTestCase):
    @staticmethod
    def _custom_docperm_has_select_field() -> bool:
        return frappe.db.has_column("Custom DocPerm", "select")

    def test_create_roles_with_homepage_normalizes_academic_staff_home_page(self):
        if frappe.db.exists("Role", "Academic Staff"):
            role = frappe.get_doc("Role", "Academic Staff")
        else:
            role = frappe.get_doc({"doctype": "Role", "role_name": "Academic Staff"}).insert(ignore_permissions=True)

        role.home_page = "/portal/staff"
        role.desk_access = 1
        role.save(ignore_permissions=True)

        create_roles_with_homepage()

        role.reload()
        self.assertEqual(role.home_page, "/hub/staff")
        self.assertEqual(int(role.desk_access or 0), 1)

    def test_ensure_canonical_role_records_creates_canonical_roles(self):
        for role_name in ("Academic Assistant", "Counselor"):
            if frappe.db.exists("Role", role_name):
                frappe.delete_doc("Role", role_name, force=1, ignore_permissions=True)

        ensure_canonical_role_records()

        self.assertTrue(frappe.db.exists("Role", "Academic Assistant"))
        self.assertTrue(frappe.db.exists("Role", "Counselor"))

    def test_grant_role_read_select_to_hr_seeds_student_log_next_step_editor_roles(self):
        editor_role = "Student Log Next Step Editor"
        if not frappe.db.exists("Role", editor_role):
            frappe.get_doc({"doctype": "Role", "role_name": editor_role, "desk_access": 1}).insert(
                ignore_permissions=True
            )

        existing_step_perms = frappe.get_all(
            "Custom DocPerm",
            filters={"parent": "Student Log Next Step", "role": editor_role, "permlevel": 0},
            pluck="name",
        )
        for docname in existing_step_perms:
            frappe.delete_doc("Custom DocPerm", docname, force=1, ignore_permissions=True)

        existing_role_perms = frappe.get_all(
            "Custom DocPerm",
            filters={"parent": "Role", "role": editor_role, "permlevel": 0},
            pluck="name",
        )
        for docname in existing_role_perms:
            frappe.delete_doc("Custom DocPerm", docname, force=1, ignore_permissions=True)

        step_docperm = frappe.new_doc("Custom DocPerm")
        step_docperm.parent = "Student Log Next Step"
        step_docperm.parenttype = "DocType"
        step_docperm.parentfield = "permissions"
        step_docperm.role = editor_role
        step_docperm.permlevel = 0
        step_docperm.read = 1
        step_docperm.write = 1
        step_docperm.insert(ignore_permissions=True)

        grant_role_read_select_to_hr()

        fields = ["read"]
        if self._custom_docperm_has_select_field():
            fields.append("select")

        role_docperm = frappe.get_value(
            "Custom DocPerm",
            {"parent": "Role", "role": editor_role, "permlevel": 0},
            fields,
            as_dict=True,
        )
        self.assertIsNotNone(role_docperm)
        self.assertEqual(int(role_docperm.read or 0), 1)
        if "select" in fields:
            self.assertEqual(int(role_docperm.select or 0), 1)

    def test_create_designations_skips_without_real_organization(self):
        with (
            patch("ifitwala_ed.setup.setup._resolve_designation_seed_organization", return_value=None),
            patch("ifitwala_ed.setup.setup.insert_record") as insert_record,
        ):
            create_designations()

        insert_record.assert_not_called()

    def test_create_designations_scopes_seed_rows_to_real_organization(self):
        with (
            patch("ifitwala_ed.setup.setup._resolve_designation_seed_organization", return_value="ORG-ROOT"),
            patch("ifitwala_ed.setup.setup.insert_record") as insert_record,
        ):
            create_designations()

        rows = insert_record.call_args.args[0]
        self.assertTrue(rows)
        self.assertTrue(all(row.get("organization") == "ORG-ROOT" for row in rows))
        self.assertEqual(rows[0].get("designation_name"), "Director")

    def test_complete_initial_setup_seeds_designations_after_first_real_organization(self):
        root_doc = _DummyDoc("All Organizations")
        org_doc = _DummyDoc("Test Organization")
        website_settings = _DummyDoc("Website Settings")
        org_setting = _DummyDoc("Org Setting")

        with (
            patch("ifitwala_ed.setup.initial_setup.is_setup_done", return_value=False),
            patch("ifitwala_ed.setup.initial_setup.frappe.db.exists", return_value=False),
            patch(
                "ifitwala_ed.setup.initial_setup.frappe.get_doc",
                side_effect=[root_doc, org_doc],
            ),
            patch(
                "ifitwala_ed.setup.initial_setup.frappe.get_single",
                side_effect=[website_settings, org_setting],
            ),
            patch("ifitwala_ed.setup.initial_setup.create_designations") as create_designations_mock,
            patch("ifitwala_ed.setup.initial_setup.frappe.db.commit"),
        ):
            result = complete_initial_setup(org_name="Test Organization", org_abbr="TO")

        create_designations_mock.assert_called_once_with()
        self.assertEqual(result["organization"], "Test Organization")
        self.assertEqual(org_setting.ifitwala_initial_setup, 1)
