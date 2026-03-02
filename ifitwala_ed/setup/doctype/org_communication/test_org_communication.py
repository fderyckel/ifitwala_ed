# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/setup/doctype/org_communication/test_org_communication.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.doctype.org_communication import org_communication as org_communication_controller


class TestOrgCommunication(FrappeTestCase):
    def test_resolve_user_base_org_uses_user_default_first(self):
        with patch(
            "ifitwala_ed.setup.doctype.org_communication.org_communication._get_user_default_from_db",
            return_value="ORG-ROOT",
        ):
            self.assertEqual(org_communication_controller._resolve_user_base_org("staff@example.com"), "ORG-ROOT")

    def test_resolve_user_base_org_falls_back_to_employee_organization(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_user_default_from_db",
                return_value=None,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_user_employee_organization",
                return_value="ORG-EMP",
            ),
        ):
            self.assertEqual(org_communication_controller._resolve_user_base_org("staff@example.com"), "ORG-EMP")

    def test_get_allowed_schools_prefers_default_school_scope(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=("SCH-ROOT", ["SCH-ROOT", "SCH-CHILD"]),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_org_scope_schools_for_user",
                return_value=["SCH-ORG"],
            ) as org_scope_schools,
        ):
            schools = org_communication_controller._get_allowed_schools_for_user("staff@example.com")

        self.assertEqual(schools, ["SCH-ROOT", "SCH-CHILD"])
        org_scope_schools.assert_not_called()

    def test_get_allowed_schools_falls_back_to_org_scope_without_default_school(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_org_scope_schools_for_user",
                return_value=["SCH-ORG-A", "SCH-ORG-B"],
            ),
        ):
            schools = org_communication_controller._get_allowed_schools_for_user("staff@example.com")

        self.assertEqual(schools, ["SCH-ORG-A", "SCH-ORG-B"])

    def test_validate_non_privileged_without_default_school_accepts_org_scoped_school(self):
        doc = frappe._dict(school="SCH-ORG-A")

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_schools_for_user",
                return_value=["SCH-ORG-A", "SCH-ORG-B"],
            ),
        ):
            org_communication_controller.OrgCommunication._validate_and_enforce_issuing_school_scope(doc)

        self.assertEqual(doc.school, "SCH-ORG-A")

    def test_validate_non_privileged_without_default_school_rejects_out_of_scope_school(self):
        doc = frappe._dict(school="SCH-OTHER")

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_schools_for_user",
                return_value=["SCH-ORG-A", "SCH-ORG-B"],
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                org_communication_controller.OrgCommunication._validate_and_enforce_issuing_school_scope(doc)

    def test_validate_school_scope_allows_blank_school(self):
        doc = frappe._dict(school=None)

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
        ):
            org_communication_controller.OrgCommunication._validate_and_enforce_issuing_school_scope(doc)

        self.assertIsNone(doc.school)

    def test_validate_organization_scope_derives_default_org(self):
        doc = frappe._dict(organization=None)

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._resolve_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._resolve_user_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            org_communication_controller.OrgCommunication._resolve_and_validate_organization_scope(doc)

        self.assertEqual(doc.organization, "ORG-ROOT")

    def test_validate_organization_scope_rejects_out_of_scope_org(self):
        doc = frappe._dict(organization="ORG-OTHER")

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._resolve_user_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                org_communication_controller.OrgCommunication._resolve_and_validate_organization_scope(doc)

    def test_school_organization_alignment_allows_descendant_school_org(self):
        doc = frappe._dict(organization="ORG-PARENT", school="SCH-CHILD")

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication.frappe.db.get_value",
                return_value="ORG-CHILD",
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_descendant_organizations_uncached",
                return_value=["ORG-PARENT", "ORG-CHILD"],
            ),
        ):
            org_communication_controller.OrgCommunication._validate_school_organization_alignment(doc)

    def test_school_organization_alignment_rejects_outside_org_scope(self):
        doc = frappe._dict(organization="ORG-PARENT", school="SCH-OTHER")

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication.frappe.db.get_value",
                return_value="ORG-SIBLING",
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_descendant_organizations_uncached",
                return_value=["ORG-PARENT", "ORG-CHILD"],
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                org_communication_controller.OrgCommunication._validate_school_organization_alignment(doc)

    def test_permission_query_conditions_supports_org_level_records(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_schools_for_user",
                return_value=[],
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_organizations_for_user",
                return_value=["ORG-ROOT"],
            ),
        ):
            conditions = org_communication_controller.get_permission_query_conditions("staff@example.com")

        self.assertIn("COALESCE(`tabOrg Communication`.`school`, '') = ''", conditions)
        self.assertIn("`tabOrg Communication`.`organization` in", conditions)

    def test_has_permission_org_level_record_within_scope(self):
        doc = frappe._dict(school=None, organization="ORG-ROOT", owner="staff@example.com", status="Draft")

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_schools_for_user",
                return_value=[],
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_organizations_for_user",
                return_value=["ORG-ROOT"],
            ),
        ):
            can_write = org_communication_controller.has_permission(doc, user="staff@example.com", ptype="write")

        self.assertTrue(can_write)

    def test_student_group_audience_validation_without_parent_school(self):
        doc = frappe._dict(
            school=None,
            audiences=[
                frappe._dict(
                    target_mode="Student Group",
                    student_group="SG-A",
                    to_staff=0,
                    to_students=1,
                    to_guardians=0,
                    to_community=0,
                )
            ],
        )

        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_allowed_schools_for_user",
                return_value=[],
            ),
        ):
            org_communication_controller.OrgCommunication._validate_audiences(doc)

    def test_context_uses_org_scope_schools_when_default_school_missing(self):
        with (
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_school_scope_tree",
                return_value=(None, []),
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._user_has_any_role",
                return_value=False,
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._get_org_scope_schools_for_user",
                return_value=["SCH-ORG-A"],
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._resolve_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.setup.doctype.org_communication.org_communication._resolve_user_org_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            ctx = org_communication_controller.get_org_communication_context()

        self.assertEqual(ctx.get("default_school"), None)
        self.assertEqual(ctx.get("default_organization"), "ORG-ROOT")
        self.assertEqual(ctx.get("allowed_organizations"), ["ORG-ROOT", "ORG-CHILD"])
        self.assertEqual(ctx.get("allowed_schools"), ["SCH-ORG-A"])
        self.assertEqual(ctx.get("lock_to_default_school"), False)
        self.assertEqual(ctx.get("can_select_school"), True)
