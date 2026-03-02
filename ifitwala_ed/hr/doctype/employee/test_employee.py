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

    def test_employee_pqc_hr_user_is_org_scoped_and_includes_unassigned(self):
        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["HR User"]),
            patch(
                "ifitwala_ed.hr.doctype.employee.employee._resolve_hr_org_scope", return_value=["ORG-ROOT", "ORG-CHILD"]
            ),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.db.escape", side_effect=lambda v: f"'{v}'"),
        ):
            condition = employee_controller.get_permission_query_conditions(user="hr.user@example.com")

        self.assertEqual(
            condition,
            "(`tabEmployee`.`organization` IN ('ORG-ROOT', 'ORG-CHILD') OR IFNULL(`tabEmployee`.`organization`, '') = '')",
        )

    def test_employee_pqc_hr_user_without_base_org_only_unassigned(self):
        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["HR User"]),
            patch("ifitwala_ed.hr.doctype.employee.employee._resolve_hr_org_scope", return_value=[]),
        ):
            condition = employee_controller.get_permission_query_conditions(user="hr.user@example.com")

        self.assertEqual(condition, "IFNULL(`tabEmployee`.`organization`, '') = ''")

    def test_employee_has_permission_hr_manager_is_org_scoped_and_includes_unassigned(self):
        allowed_doc = frappe._dict(organization="ORG-CHILD", school="SCH-001")
        blocked_doc = frappe._dict(organization="ORG-OTHER", school="SCH-001")
        unassigned_doc = frappe._dict(organization="", school="SCH-001")

        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["HR Manager"]),
            patch(
                "ifitwala_ed.hr.doctype.employee.employee._resolve_hr_org_scope", return_value=["ORG-ROOT", "ORG-CHILD"]
            ),
        ):
            self.assertTrue(employee_controller.employee_has_permission(allowed_doc, "read", "hr.manager@example.com"))
            self.assertFalse(employee_controller.employee_has_permission(blocked_doc, "read", "hr.manager@example.com"))
            self.assertTrue(
                employee_controller.employee_has_permission(unassigned_doc, "read", "hr.manager@example.com")
            )

    def test_resolve_hr_org_scope_includes_user_permission_org_descendants(self):
        with (
            patch("ifitwala_ed.hr.doctype.employee.employee._resolve_hr_base_org", return_value=None),
            patch(
                "ifitwala_ed.hr.doctype.employee.employee.frappe.get_all",
                return_value=["ORG-PARENT"],
            ),
            patch(
                "ifitwala_ed.hr.doctype.employee.employee._get_descendant_organizations_uncached",
                return_value=["ORG-PARENT", "ORG-CHILD"],
            ),
        ):
            scope = employee_controller._resolve_hr_org_scope("hr.user@example.com")

        self.assertEqual(scope, ["ORG-CHILD", "ORG-PARENT"])

    def test_resolve_hr_base_org_uses_user_default_org_first(self):
        with (
            patch(
                "ifitwala_ed.hr.doctype.employee.employee._get_user_default_from_db",
                return_value="ORG-DEFAULT",
            ),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.db.get_single_value", return_value="ORG-GLOBAL"),
        ):
            base_org = employee_controller._resolve_hr_base_org("hr.user@example.com")

        self.assertEqual(base_org, "ORG-DEFAULT")

    def test_resolve_hr_base_org_falls_back_to_global_default_org(self):
        with (
            patch(
                "ifitwala_ed.hr.doctype.employee.employee._get_user_default_from_db",
                return_value=None,
            ),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.db.get_single_value", return_value="ORG-GLOBAL"),
        ):
            base_org = employee_controller._resolve_hr_base_org("hr.user@example.com")

        self.assertEqual(base_org, "ORG-GLOBAL")

    def test_employee_tree_roots_include_visible_rows_with_out_of_scope_manager(self):
        all_visible = [
            frappe._dict(value="EMP-0001", title="Rootless Child", reports_to="MGR-OUT"),
            frappe._dict(value="EMP-0002", title="Top Root", reports_to=""),
        ]

        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_list", return_value=all_visible),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.db.sql", return_value=[]),
        ):
            rows = employee_controller.get_children("Employee", parent="", is_root=True)

        self.assertEqual({row.get("value") for row in rows}, {"EMP-0001", "EMP-0002"})

    def test_employee_pqc_academic_admin_remains_school_scoped(self):
        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.hr.doctype.employee.employee._get_user_default_from_db", return_value="SCH-ROOT"),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.db.escape", side_effect=lambda v: f"'{v}'"),
        ):
            condition = employee_controller.get_permission_query_conditions(user="academic.admin@example.com")

        self.assertEqual(condition, "`tabEmployee`.`school` = 'SCH-ROOT'")

    def test_employee_has_permission_academic_admin_stays_scoped(self):
        allowed_doc = frappe._dict(school="SCH-ROOT")
        blocked_doc = frappe._dict(school="SCH-OTHER")

        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.hr.doctype.employee.employee._get_user_default_from_db", return_value="SCH-ROOT"),
        ):
            self.assertTrue(employee_controller.employee_has_permission(allowed_doc, "read", "aa@example.com"))
            self.assertFalse(employee_controller.employee_has_permission(blocked_doc, "read", "aa@example.com"))
            self.assertFalse(employee_controller.employee_has_permission(allowed_doc, "write", "aa@example.com"))

    def test_employee_has_permission_hr_write_is_scoped(self):
        allowed_doc = frappe._dict(organization="ORG-CHILD")
        blocked_doc = frappe._dict(organization="ORG-OTHER")

        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["HR User"]),
            patch(
                "ifitwala_ed.hr.doctype.employee.employee._resolve_hr_org_scope", return_value=["ORG-ROOT", "ORG-CHILD"]
            ),
        ):
            self.assertTrue(employee_controller.employee_has_permission(allowed_doc, "write", "hr.user@example.com"))
            self.assertFalse(employee_controller.employee_has_permission(blocked_doc, "write", "hr.user@example.com"))

    def test_employee_pqc_employee_role_is_self_only(self):
        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["Employee"]),
            patch("ifitwala_ed.hr.doctype.employee.employee._resolve_self_employee", return_value="HR-EMP-1234"),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.db.escape", side_effect=lambda v: f"'{v}'"),
        ):
            condition = employee_controller.get_permission_query_conditions(user="employee.user@example.com")

        self.assertEqual(condition, "`tabEmployee`.`name` = 'HR-EMP-1234'")

    def test_employee_has_permission_employee_role_is_self_only(self):
        own_doc = frappe._dict(name="HR-EMP-1234", user_id="employee.user@example.com")
        other_doc = frappe._dict(name="HR-EMP-9999", user_id="other.user@example.com")

        with (
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.get_roles", return_value=["Employee"]),
            patch("ifitwala_ed.hr.doctype.employee.employee._resolve_self_employee", return_value="HR-EMP-1234"),
        ):
            self.assertTrue(employee_controller.employee_has_permission(own_doc, "read", "employee.user@example.com"))
            self.assertFalse(
                employee_controller.employee_has_permission(other_doc, "read", "employee.user@example.com")
            )
            self.assertFalse(employee_controller.employee_has_permission(own_doc, "write", "employee.user@example.com"))

    def test_update_user_default_organization_sets_on_first_time(self):
        emp = employee_controller.Employee.__new__(employee_controller.Employee)
        emp.user_id = "staff@example.com"
        emp.organization = "Ifitwala Education Org"

        with (
            patch("ifitwala_ed.hr.doctype.employee.employee._get_user_default_from_db", return_value=None),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.defaults.set_user_default") as set_default,
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.cache") as cache_mock,
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.msgprint"),
        ):
            emp.update_user_default_organization()

        set_default.assert_called_once_with("organization", "Ifitwala Education Org", "staff@example.com")
        cache_mock.return_value.hdel.assert_called_once_with("user:staff@example.com", "defaults")

    def test_update_user_default_organization_clears_when_empty(self):
        emp = employee_controller.Employee.__new__(employee_controller.Employee)
        emp.user_id = "staff@example.com"
        emp.organization = ""

        with (
            patch(
                "ifitwala_ed.hr.doctype.employee.employee._get_user_default_from_db",
                return_value="Ifitwala Canopy Campus",
            ),
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.defaults.clear_default") as clear_default,
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.cache") as cache_mock,
            patch("ifitwala_ed.hr.doctype.employee.employee.frappe.msgprint"),
        ):
            emp.update_user_default_organization()

        clear_default.assert_called_once_with("organization", "staff@example.com")
        cache_mock.return_value.hdel.assert_called_once_with("user:staff@example.com", "defaults")

    def test_on_update_syncs_defaults_even_when_profile_sync_not_allowed(self):
        emp = employee_controller.Employee.__new__(employee_controller.Employee)
        emp.user_id = "staff@example.com"

        with (
            patch.object(emp, "_reports_to_changed", return_value=False),
            patch.object(emp, "reset_employee_emails_cache"),
            patch.object(emp, "sync_employee_history"),
            patch.object(emp, "_sync_staff_calendar"),
            patch.object(emp, "_ensure_primary_contact"),
            patch.object(emp, "_apply_designation_role"),
            patch.object(emp, "_apply_approver_roles"),
            patch.object(emp, "_can_sync_user_profile", return_value=False),
            patch.object(emp, "update_user") as update_user,
            patch.object(emp, "update_user_default_organization") as update_org,
            patch.object(emp, "update_user_default_school") as update_school,
        ):
            emp.on_update()

        update_user.assert_not_called()
        update_org.assert_called_once()
        update_school.assert_called_once()
