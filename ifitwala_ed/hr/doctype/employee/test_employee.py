# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from ifitwala_ed.hr import employee_access
from ifitwala_ed.hr.doctype.employee import employee as employee_controller


class TestEmployee(FrappeTestCase):
    def test_compute_effective_access_uses_role_links_from_current_history(self):
        emp = frappe._dict(
            designation="Teacher",
            date_of_joining=nowdate(),
            employee_history=[
                frappe._dict(
                    {
                        "designation": "Teacher",
                        "is_current": 1,
                        "access_mode": "Override",
                        "role_profile": "Academic Staff",
                        "workspace_override": "Academics",
                        "priority": 20,
                    }
                ),
                frappe._dict(
                    {
                        "designation": "Grade Leader",
                        "is_current": 1,
                        "access_mode": "Override",
                        "role_profile": "School Data Analyst",
                        "workspace_override": "Admin",
                        "priority": 5,
                    }
                ),
            ],
        )

        with patch(
            "ifitwala_ed.hr.employee_access._roles_from_role_name",
            side_effect=lambda role_name: {role_name} if role_name else set(),
        ):
            roles, workspace = employee_access.compute_effective_access_from_employee(emp)

        self.assertEqual(roles, {"Academic Staff", "School Data Analyst"})
        self.assertEqual(workspace, "Academics")

    def test_compute_effective_access_prejoin_assigns_baseline_role_only(self):
        emp = frappe._dict(
            designation="Teacher",
            date_of_joining=add_days(nowdate(), 3),
            employee_history=[],
        )

        with patch(
            "ifitwala_ed.hr.employee_access._designation_defaults",
            return_value={
                "roles": {"Academic Staff"},
                "workspace": "Academics",
                "priority": 10,
            },
        ):
            roles, workspace = employee_access.compute_effective_access_from_employee(emp)

        self.assertEqual(roles, {"Academic Staff"})
        self.assertIsNone(workspace)

    def test_compute_effective_access_no_active_rows_returns_empty_for_started_employee(self):
        emp = frappe._dict(
            designation="Teacher",
            date_of_joining=add_days(nowdate(), -3),
            employee_history=[],
        )

        with patch("ifitwala_ed.hr.employee_access._designation_defaults") as designation_defaults:
            roles, workspace = employee_access.compute_effective_access_from_employee(emp)

        designation_defaults.assert_not_called()
        self.assertEqual(roles, set())
        self.assertIsNone(workspace)

    def test_sync_user_access_disables_non_active_employee_user(self):
        emp = frappe._dict(
            user_id="nonactive.employee@example.com",
            employment_status="Temporary Leave",
            employee_history=[],
        )
        user_doc = frappe._dict(default_workspace=None, user_type="System User", enabled=1)
        user_doc.save = Mock()

        with (
            patch(
                "ifitwala_ed.hr.employee_access.compute_effective_access_from_employee",
                return_value=(set(), None),
            ) as compute_access,
            patch("ifitwala_ed.hr.employee_access._diff_user_roles", return_value=(set(), [])) as diff_roles,
            patch("ifitwala_ed.hr.employee_access.frappe.get_doc", return_value=user_doc),
        ):
            employee_access.sync_user_access_from_employee(emp)

        compute_access.assert_not_called()
        diff_roles.assert_not_called()
        self.assertEqual(user_doc.enabled, 0)
        user_doc.save.assert_called_once_with(ignore_permissions=True)

    def test_sync_user_access_enables_active_employee_user(self):
        emp = frappe._dict(
            user_id="active.employee@example.com",
            employment_status="Active",
            employee_history=[],
        )
        user_doc = frappe._dict(default_workspace=None, user_type="System User", enabled=0)
        user_doc.save = Mock()

        with (
            patch(
                "ifitwala_ed.hr.employee_access.compute_effective_access_from_employee",
                return_value=(set(), None),
            ) as compute_access,
            patch("ifitwala_ed.hr.employee_access._diff_user_roles", return_value=(set(), [])),
            patch("ifitwala_ed.hr.employee_access.frappe.get_doc", return_value=user_doc),
        ):
            employee_access.sync_user_access_from_employee(emp)

        compute_access.assert_called_once_with(emp)
        self.assertEqual(user_doc.enabled, 1)
        user_doc.save.assert_called_once_with(ignore_permissions=True)

    def test_employee_pqc_hr_user_is_global(self):
        with patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["HR User"]):
            self.assertIsNone(employee_controller.get_permission_query_conditions(user="hr.user@example.com"))

    def test_employee_has_permission_hr_manager_is_global(self):
        doc = frappe._dict(organization="ORG-001", school="SCH-001")

        with patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["HR Manager"]):
            self.assertTrue(employee_controller.employee_has_permission(doc, "read", "hr.manager@example.com"))
            self.assertTrue(employee_controller.employee_has_permission(doc, "write", "hr.manager@example.com"))

    def test_employee_pqc_academic_admin_remains_school_scoped(self):
        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.hr.doctype.employee.employee.get_user_base_school", return_value="SCH-ROOT"),
            patch(
                "ifitwala_ed.hr.doctype.employee.employee.get_descendant_schools",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.db.escape", side_effect=lambda v: f"'{v}'"),
        ):
            condition = employee_controller.get_permission_query_conditions(user="academic.admin@example.com")

        self.assertEqual(condition, "`tabEmployee`.`school` IN ('SCH-ROOT', 'SCH-CHILD')")

    def test_employee_has_permission_academic_admin_stays_scoped(self):
        allowed_doc = frappe._dict(school="SCH-CHILD")
        blocked_doc = frappe._dict(school="SCH-OTHER")

        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.hr.doctype.employee.employee.get_user_base_school", return_value="SCH-ROOT"),
            patch(
                "ifitwala_ed.hr.doctype.employee.employee.get_descendant_schools",
                return_value=["SCH-ROOT", "SCH-CHILD"],
            ),
        ):
            self.assertTrue(employee_controller.employee_has_permission(allowed_doc, "read", "aa@example.com"))
            self.assertFalse(employee_controller.employee_has_permission(blocked_doc, "read", "aa@example.com"))
