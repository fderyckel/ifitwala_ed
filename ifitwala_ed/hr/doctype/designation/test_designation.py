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

    def test_designation_pqc_operator_scope_uses_read_org_and_school_scope(self):
        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_org_scope",
                return_value=["All Organizations", "ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_school_scope",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.db.escape", side_effect=lambda v: f"'{v}'"),
        ):
            condition = designation_controller.get_permission_query_conditions(user="hr.manager@example.com")

        self.assertEqual(
            condition,
            "(`tabDesignation`.`organization` IN ('All Organizations', 'ORG-ROOT', 'ORG-CHILD') "
            "AND (IFNULL(`tabDesignation`.`school`, '') = '' OR `tabDesignation`.`school` IN ('SCH-ROOT', 'SCH-CHILD')))",
        )

    def test_designation_pqc_academic_admin_uses_org_and_school_ancestors(self):
        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Academic Admin"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_org_scope",
                return_value=["All Organizations", "ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_school_scope",
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

    def test_can_user_read_designation_academic_admin_does_not_read_all_organizations_row(self):
        doc = frappe._dict(organization="All Organizations", school="")

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Academic Admin"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_org_scope",
                return_value=["ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_school_scope",
                return_value=None,
            ),
        ):
            allowed = designation_controller._can_user_read_designation(doc, user="academic.admin@example.com")

        self.assertFalse(allowed)

    def test_can_user_read_designation_non_operator_school_scope_flows_to_child_school_user(self):
        doc = frappe._dict(organization="ORG-ROOT", school="SCH-ROOT")

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Instructor"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_org_scope",
                return_value=["All Organizations", "ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_school_scope",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
        ):
            allowed = designation_controller._can_user_read_designation(doc, user="instructor@example.com")

        self.assertTrue(allowed)

    def test_assert_mutation_scope_allowed_operator_save_uses_descendant_org_scope_only(self):
        doc = designation_controller.Designation.__new__(designation_controller.Designation)
        doc.organization = "ORG-ROOT"
        doc.school = ""

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_operator_org_scope",
                return_value=["All Organizations", "ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            doc._assert_mutation_scope_allowed("save", user="hr.manager@example.com")

    def test_assert_mutation_scope_allowed_blocks_outside_org_scope(self):
        doc = designation_controller.Designation.__new__(designation_controller.Designation)
        doc.organization = "ORG-PARENT"
        doc.school = ""

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_operator_org_scope",
                return_value=["All Organizations", "ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                doc._assert_mutation_scope_allowed("save", user="hr.manager@example.com")

    def test_assert_mutation_scope_allowed_blocks_sibling_school(self):
        doc = designation_controller.Designation.__new__(designation_controller.Designation)
        doc.organization = "ORG-ROOT"
        doc.school = "SCH-SIBLING"

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_operator_org_scope",
                return_value=["All Organizations", "ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_operator_school_write_scope",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                doc._assert_mutation_scope_allowed("save", user="hr.manager@example.com")

    def test_can_user_read_designation_non_operator_blocks_sibling_school_user(self):
        doc = frappe._dict(organization="ORG-ROOT", school="SCH-ROOT")

        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Academic Assistant"]
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_org_scope",
                return_value=["All Organizations", "ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_read_school_scope",
                return_value=["SCH-OTHER"],
            ),
        ):
            allowed = designation_controller._can_user_read_designation(doc, user="academic.assistant@example.com")

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

    def test_resolve_designation_read_org_scope_for_operator_includes_ancestors_and_descendants(self):
        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_org",
                return_value="ORG-CHILD",
            ),
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.db.exists", return_value=True),
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
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_descendant_organizations_uncached",
                side_effect=lambda org: {
                    "ORG-CHILD": ["ORG-CHILD", "ORG-GRANDCHILD"],
                    "ORG-EXPLICIT": ["ORG-EXPLICIT", "ORG-EXPLICIT-CHILD"],
                }[org],
            ),
        ):
            scope = designation_controller._resolve_designation_read_org_scope(
                "hr.manager@example.com",
                roles={"HR Manager"},
            )

        self.assertEqual(
            scope,
            [
                "All Organizations",
                "ORG-CHILD",
                "ORG-EXPLICIT",
                "ORG-EXPLICIT-CHILD",
                "ORG-GRANDCHILD",
                "ORG-OTHER",
                "ORG-ROOT",
            ],
        )

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

    def test_resolve_designation_read_school_scope_for_operator_uses_ancestor_and_descendant_schools(self):
        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_school",
                return_value="SCH-CHILD",
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_ancestor_schools_uncached",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_descendant_schools_uncached",
                return_value=["SCH-CHILD", "SCH-GRANDCHILD"],
            ),
        ):
            scope = designation_controller._resolve_designation_read_school_scope(
                "hr.manager@example.com",
                roles={"HR Manager"},
                org_scope=["ORG-ROOT"],
            )

        self.assertEqual(scope, ["SCH-CHILD", "SCH-GRANDCHILD", "SCH-ROOT"])

    def test_get_default_designation_organization_uses_resolved_user_org(self):
        with patch(
            "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_org",
            return_value="ORG-ROOT",
        ):
            organization = designation_controller.get_default_designation_organization()

        self.assertEqual(organization, "ORG-ROOT")

    def test_get_scoped_designation_employees_denies_non_hr_lookup(self):
        designation_doc = frappe._dict(name="Teacher", designation_name="Teacher", organization="ORG-ROOT", school="")

        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation.frappe.session",
                frappe._dict(user="academic.admin@example.com"),
            ),
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_doc", return_value=designation_doc),
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["Academic Admin"]),
        ):
            with self.assertRaises(frappe.PermissionError):
                designation_controller.get_scoped_designation_employees("Teacher")

    def test_resolve_designation_employee_school_scope_intersects_descendants(self):
        designation_doc = frappe._dict(school="SCH-ROOT")

        with (
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_user_base_school",
                return_value="SCH-CHILD",
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_descendant_schools_uncached",
                side_effect=lambda school: {
                    "SCH-CHILD": ["SCH-CHILD", "SCH-GRANDCHILD"],
                    "SCH-ROOT": ["SCH-ROOT", "SCH-CHILD", "SCH-GRANDCHILD"],
                }[school],
            ),
        ):
            schools, allow_blank = designation_controller._resolve_designation_employee_school_scope(
                designation_doc,
                "hr.manager@example.com",
                org_scope=["ORG-ROOT"],
            )

        self.assertEqual(schools, ["SCH-CHILD", "SCH-GRANDCHILD"])
        self.assertFalse(allow_blank)

    def test_get_current_history_designation_matches_filters_on_current_rows(self):
        with patch("ifitwala_ed.hr.doctype.designation.designation.frappe.db.sql", return_value=[]) as sql:
            designation_controller._get_current_history_designation_matches(
                designation="Teacher",
                org_scope=["ORG-ROOT"],
                school_scope=["SCH-ROOT"],
                allow_blank_school=False,
            )

        query = sql.call_args.args[0]
        params = sql.call_args.args[1]

        self.assertIn("COALESCE(hist.is_current, 0) = 1", query)
        self.assertEqual(params[:3], ["Active", "Employee", "Teacher"])

    def test_get_scoped_designation_employees_merges_primary_and_current_history(self):
        designation_doc = frappe._dict(name="Teacher", designation_name="Teacher", organization="ORG-ROOT", school="")

        primary_rows = [
            frappe._dict(
                {
                    "employee": "EMP-001",
                    "employee_full_name": "Ada Lovelace",
                    "user_id": "ada@example.com",
                    "organization": "ORG-ROOT",
                    "school": "SCH-ROOT",
                }
            )
        ]
        history_rows = [
            frappe._dict(
                {
                    "employee": "EMP-001",
                    "employee_full_name": "Ada Lovelace",
                    "user_id": "ada@example.com",
                    "organization": "ORG-ROOT",
                    "school": "SCH-ROOT",
                    "from_date": "2026-01-01",
                }
            ),
            frappe._dict(
                {
                    "employee": "EMP-002",
                    "employee_full_name": "Grace Hopper",
                    "user_id": "grace@example.com",
                    "organization": "ORG-ROOT",
                    "school": "SCH-CHILD",
                    "from_date": "2026-02-01",
                }
            ),
        ]

        with (
            patch(
                "ifitwala_ed.hr.doctype.designation.designation.frappe.session",
                frappe._dict(user="hr.manager@example.com"),
            ),
            patch("ifitwala_ed.hr.doctype.designation.designation.frappe.get_doc", return_value=designation_doc),
            patch("ifitwala_ed.hr.doctype.designation.designation._assert_designation_employee_lookup_allowed"),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_employee_org_scope",
                return_value=["ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._resolve_designation_employee_school_scope",
                return_value=(["SCH-ROOT", "SCH-CHILD"], True),
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_primary_designation_employee_matches",
                return_value=primary_rows,
            ),
            patch(
                "ifitwala_ed.hr.doctype.designation.designation._get_current_history_designation_matches",
                return_value=history_rows,
            ),
        ):
            payload = designation_controller.get_scoped_designation_employees("Teacher")

        self.assertEqual(payload["count"], 2)
        self.assertEqual([row["employee"] for row in payload["employees"]], ["EMP-001", "EMP-002"])
        self.assertEqual(payload["employees"][0]["match_sources"], ["Current history", "Primary designation"])
        self.assertEqual(payload["employees"][0]["history_matches"][0]["from_date"], "2026-01-01")
        self.assertEqual(payload["employees"][1]["match_sources"], ["Current history"])
