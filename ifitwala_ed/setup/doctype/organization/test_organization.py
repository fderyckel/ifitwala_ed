# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.doctype.organization import organization as organization_controller


class TestOrganization(FrappeTestCase):
    def test_org_pqc_hr_scoped(self):
        with (
            patch("ifitwala_ed.setup.doctype.organization.organization.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.setup.doctype.organization.organization._resolve_hr_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.setup.doctype.organization.organization.frappe.db.escape", side_effect=lambda v: f"'{v}'"
            ),
        ):
            condition = organization_controller.get_permission_query_conditions(user="hr.manager@example.com")

        self.assertEqual(condition, "`tabOrganization`.`name` IN ('ORG-ROOT', 'ORG-CHILD')")

    def test_org_has_permission_hr_scoped(self):
        allowed_doc = frappe._dict(name="ORG-CHILD")
        blocked_doc = frappe._dict(name="ORG-OTHER")

        with (
            patch("ifitwala_ed.setup.doctype.organization.organization.frappe.get_roles", return_value=["HR User"]),
            patch(
                "ifitwala_ed.setup.doctype.organization.organization._resolve_hr_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            self.assertTrue(
                organization_controller.has_permission(allowed_doc, ptype="read", user="hr.user@example.com")
            )
            self.assertFalse(
                organization_controller.has_permission(blocked_doc, ptype="read", user="hr.user@example.com")
            )

    def test_org_get_children_root_includes_scoped_nodes_with_out_of_scope_parent(self):
        all_visible = [
            frappe._dict(
                value="ORG-CHILD",
                title="Child Org",
                expandable=0,
                parent_organization="ORG-OUTSIDE",
            ),
        ]

        with patch("ifitwala_ed.setup.doctype.organization.organization.frappe.get_all", return_value=all_visible):
            rows = organization_controller.get_children("Organization", parent="", is_root=True)

        self.assertEqual([row.get("value") for row in rows], ["ORG-CHILD"])

    def test_resolve_hr_base_org_uses_user_default_then_global(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.organization.organization.frappe.defaults.get_user_default",
                return_value="ORG-DEFAULT",
            ),
            patch(
                "ifitwala_ed.setup.doctype.organization.organization.frappe.db.get_single_value",
                return_value="ORG-GLOBAL",
            ),
        ):
            self.assertEqual(organization_controller._resolve_hr_base_org("hr.user@example.com"), "ORG-DEFAULT")

        with (
            patch(
                "ifitwala_ed.setup.doctype.organization.organization.frappe.defaults.get_user_default",
                return_value=None,
            ),
            patch(
                "ifitwala_ed.setup.doctype.organization.organization.frappe.db.get_single_value",
                return_value="ORG-GLOBAL",
            ),
        ):
            self.assertEqual(organization_controller._resolve_hr_base_org("hr.user@example.com"), "ORG-GLOBAL")

    def test_resolve_hr_org_scope_unions_explicit_user_permission_descendants(self):
        with (
            patch("ifitwala_ed.setup.doctype.organization.organization._resolve_hr_base_org", return_value=None),
            patch(
                "ifitwala_ed.setup.doctype.organization.organization.frappe.get_all",
                return_value=["ORG-PARENT"],
            ),
            patch(
                "ifitwala_ed.setup.doctype.organization.organization.get_descendant_organizations",
                return_value=["ORG-PARENT", "ORG-CHILD"],
            ),
        ):
            scope = organization_controller._resolve_hr_org_scope("hr.user@example.com")

        self.assertEqual(scope, ["ORG-CHILD", "ORG-PARENT"])
