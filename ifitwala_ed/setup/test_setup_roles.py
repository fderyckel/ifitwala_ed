# ifitwala_ed/setup/test_setup_roles.py

from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.initial_setup import complete_initial_setup
from ifitwala_ed.setup.setup import create_designations, create_roles_with_homepage, ensure_canonical_role_records


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
