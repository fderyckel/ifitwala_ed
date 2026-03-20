# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.hr.doctype.designation import designation as designation_controller


class TestDesignation(FrappeTestCase):
    def test_validate_organization_scope_requires_real_organization(self):
        doc = designation_controller.Designation.__new__(designation_controller.Designation)
        doc.organization = "All Organizations"

        with self.assertRaises(frappe.ValidationError):
            doc.validate_organization_scope()

    def test_designation_pqc_operator_scope_uses_org_descendants(self):
        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_operator_org_scope",
                return_value=["All Organizations", "ORG-ROOT", "ORG-CHILD"],
            ),
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.db.escape", side_effect=lambda v: f"'{v}'"),
        ):
            condition = designation_controller.get_permission_query_conditions(user="hr.manager@example.com")

        self.assertEqual(
            condition,
            "(`tabDesignation`.`organization` IN ('All Organizations', 'ORG-ROOT', 'ORG-CHILD') AND 1=1)",
        )

    def test_designation_pqc_academic_admin_uses_org_and_school_ancestors(self):
        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Academic Admin"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_applicable_org_scope",
                return_value=["All Organizations", "ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_school_scope",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.db.escape", side_effect=lambda v: f"'{v}'"),
        ):
            condition = designation_controller.get_permission_query_conditions(user="academic.admin@example.com")

        self.assertEqual(
            condition,
            "(`tabDesignation`.`organization` IN ('All Organizations', 'ORG-ROOT', 'ORG-CHILD') "
            "AND (IFNULL(`tabDesignation`.`school`, '') = '' OR `tabDesignation`.`school` IN ('SCH-ROOT', 'SCH-CHILD')))",
        )

    def test_designation_has_permission_academic_admin_does_not_read_all_organizations_row(self):
        doc = frappe._dict(organization="All Organizations", school="")

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Academic Admin"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_applicable_org_scope",
                return_value=["ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_school_scope",
                return_value=None,
            ),
        ):
            allowed = designation_controller.has_permission(doc, ptype="read", user="academic.admin@example.com")

        self.assertFalse(allowed)

    def test_designation_has_permission_academic_admin_cannot_write(self):
        doc = frappe._dict(organization="ORG-ROOT", school="")

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Academic Admin"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_applicable_org_scope",
                return_value=["All Organizations", "ORG-ROOT"],
            ),
        ):
            allowed = designation_controller.has_permission(doc, ptype="write", user="academic.admin@example.com")

        self.assertFalse(allowed)

    def test_designation_has_permission_non_operator_school_scope_flows_to_child_school_user(self):
        doc = frappe._dict(organization="ORG-ROOT", school="SCH-ROOT")

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Instructor"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_applicable_org_scope",
                return_value=["All Organizations", "ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_school_scope",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
        ):
            allowed = designation_controller.has_permission(doc, ptype="read", user="instructor@example.com")

        self.assertTrue(allowed)

    def test_designation_has_permission_operator_write_uses_descendant_org_scope_only(self):
        doc = frappe._dict(organization="ORG-ROOT", school="SCH-ROOT")

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_operator_org_scope",
                return_value=["All Organizations", "ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            allowed = designation_controller.has_permission(doc, ptype="write", user="hr.manager@example.com")

        self.assertTrue(allowed)

    def test_designation_has_permission_non_operator_blocks_sibling_school_user(self):
        doc = frappe._dict(organization="ORG-ROOT", school="SCH-ROOT")

        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Academic Assistant"]
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_applicable_org_scope",
                return_value=["All Organizations", "ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_school_scope",
                return_value=["SCH-OTHER"],
            ),
        ):
            allowed = designation_controller.has_permission(doc, ptype="read", user="academic.assistant@example.com")

        self.assertFalse(allowed)

    def test_resolve_designation_applicable_org_scope_uses_user_org_ancestors_and_explicit_org_permissions(self):
        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_org",
                return_value="ORG-CHILD",
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation.frappe.get_all",
                return_value=["ORG-EXPLICIT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_ancestor_organizations_uncached",
                side_effect=lambda org: {
                    "ORG-CHILD": ["All Organizations", "ORG-ROOT", "ORG-CHILD"],
                    "ORG-EXPLICIT": ["All Organizations", "ORG-OTHER", "ORG-EXPLICIT"],
                }[org],
            ),
        ):
            scope = designation_controller._resolve_designation_applicable_org_scope("staff@example.com")

        self.assertEqual(scope, ["ORG-CHILD", "ORG-EXPLICIT", "ORG-OTHER", "ORG-ROOT"])

    def test_resolve_designation_operator_org_scope_uses_user_org_descendants_and_explicit_org_permissions(self):
        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.db.exists", return_value=True),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation.frappe.get_all",
                return_value=["ORG-EXPLICIT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_descendant_organizations_uncached",
                side_effect=lambda org: {
                    "ORG-ROOT": ["ORG-ROOT", "ORG-CHILD"],
                    "ORG-EXPLICIT": ["ORG-EXPLICIT", "ORG-EXPLICIT-CHILD"],
                }[org],
            ),
        ):
            scope = designation_controller._resolve_designation_operator_org_scope("staff@example.com")

        self.assertEqual(scope, ["All Organizations", "ORG-CHILD", "ORG-EXPLICIT", "ORG-EXPLICIT-CHILD", "ORG-ROOT"])

    def test_resolve_designation_school_scope_uses_school_ancestors(self):
        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_school",
                return_value="SCH-CHILD",
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_ancestor_schools_uncached",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
        ):
            scope = designation_controller._resolve_designation_school_scope("staff@example.com")

        self.assertEqual(scope, ["SCH-ROOT", "SCH-CHILD"])

    def test_resolve_designation_school_scope_returns_none_when_user_has_no_school(self):
        with patch(
            "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_school",
            return_value=None,
        ):
            scope = designation_controller._resolve_designation_school_scope("staff@example.com")

        self.assertIsNone(scope)

    def test_get_default_designation_organization_uses_resolved_user_org(self):
        with patch(
            "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_org",
            return_value="ORG-ROOT",
        ):
            organization = designation_controller.get_default_designation_organization()

        self.assertEqual(organization, "ORG-ROOT")
