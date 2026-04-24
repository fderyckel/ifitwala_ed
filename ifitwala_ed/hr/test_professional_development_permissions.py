# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.hr import professional_development_permissions as pd_permissions


class TestProfessionalDevelopmentPermissions(FrappeTestCase):
    def test_request_pqc_is_org_and_school_scoped_for_hr(self):
        with (
            patch(
                "ifitwala_ed.hr.professional_development_permissions.frappe.get_roles",
                return_value=["HR User"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_descendant_organizations",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_user_base_school",
                return_value="SCH-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_descendant_schools",
                return_value=["SCH-ROOT", "SCH-LEAF"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.frappe.db.escape",
                side_effect=lambda value: f"'{value}'",
            ),
        ):
            condition = pd_permissions.professional_development_request_pqc(user="hr.user@example.com")

        self.assertEqual(
            condition,
            "(`tabProfessional Development Request`.`organization` IN ('ORG-CHILD', 'ORG-ROOT')) AND "
            "((`tabProfessional Development Request`.`school` IN ('SCH-LEAF', 'SCH-ROOT') OR "
            "COALESCE(`tabProfessional Development Request`.`school`, '') = ''))",
        )

    def test_request_pqc_is_self_scoped_for_employee(self):
        with (
            patch(
                "ifitwala_ed.hr.professional_development_permissions.frappe.get_roles",
                return_value=["Employee"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.frappe.db.get_value",
                return_value="HR-EMP-0001",
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.frappe.db.escape",
                side_effect=lambda value: f"'{value}'",
            ),
        ):
            condition = pd_permissions.professional_development_request_pqc(user="staff@example.com")

        self.assertEqual(condition, "`tabProfessional Development Request`.`employee` = 'HR-EMP-0001'")

    def test_request_pqc_is_org_and_school_scoped_for_system_manager(self):
        with (
            patch(
                "ifitwala_ed.hr.professional_development_permissions.frappe.get_roles",
                return_value=["System Manager"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_descendant_organizations",
                return_value=["ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_user_base_school",
                return_value="SCH-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_descendant_schools",
                return_value=["SCH-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.frappe.db.escape",
                side_effect=lambda value: f"'{value}'",
            ),
        ):
            condition = pd_permissions.professional_development_request_pqc(user="system.manager@example.com")

        self.assertEqual(
            condition,
            "(`tabProfessional Development Request`.`organization` IN ('ORG-ROOT')) AND "
            "((`tabProfessional Development Request`.`school` IN ('SCH-ROOT') OR "
            "COALESCE(`tabProfessional Development Request`.`school`, '') = ''))",
        )

    def test_administrator_remains_unrestricted(self):
        condition = pd_permissions.professional_development_request_pqc(user="Administrator")

        self.assertIsNone(condition)

    def test_system_manager_doc_permission_is_scope_checked(self):
        doc = frappe._dict(
            doctype="Professional Development Request",
            organization="ORG-OTHER",
            school="SCH-ROOT",
            employee="HR-EMP-0001",
        )
        with (
            patch(
                "ifitwala_ed.hr.professional_development_permissions.frappe.get_roles",
                return_value=["System Manager"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_descendant_organizations",
                return_value=["ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_user_base_school",
                return_value="SCH-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.professional_development_permissions.get_descendant_schools",
                return_value=["SCH-ROOT"],
            ),
        ):
            allowed = pd_permissions.professional_development_request_has_permission(
                doc,
                user="system.manager@example.com",
                ptype="read",
            )

        self.assertFalse(allowed)
