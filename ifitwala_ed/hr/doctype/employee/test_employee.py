# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from ifitwala_ed.hr import employee_access


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
