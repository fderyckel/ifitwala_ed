# ifitwala_ed/hr/test_leave_permissions.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.hr import leave_permissions


class TestLeavePermissions(FrappeTestCase):
	def test_non_hr_user_gets_employee_only_query_condition(self):
		with (
			patch("frappe.get_roles", return_value=["Employee"]),
			patch("ifitwala_ed.hr.leave_permissions._is_system_or_hr", return_value=False),
			patch("ifitwala_ed.hr.leave_permissions._get_employee_for_user", return_value="HR-EMP-0001"),
		):
			condition = leave_permissions.get_permission_query_conditions(
				"Leave Application",
				"user@example.com",
			)

		self.assertIn("`tabLeave Application`.`employee`", condition)
		self.assertIn("HR-EMP-0001", condition)

	def test_hr_user_gets_organization_subtree_condition(self):
		with (
			patch("frappe.get_roles", return_value=["HR User"]),
			patch("ifitwala_ed.hr.leave_permissions._is_system_or_hr", return_value=True),
			patch("ifitwala_ed.hr.leave_permissions._get_user_org_scope", return_value=["Org A", "Org B"]),
		):
			condition = leave_permissions.get_permission_query_conditions(
				"Leave Application",
				"hr@example.com",
			)

		self.assertIn("`tabLeave Application`.`organization` IN", condition)
		self.assertIn("Org A", condition)
		self.assertIn("Org B", condition)

	def test_academic_admin_gets_organization_subtree_condition(self):
		with (
			patch("frappe.get_roles", return_value=["Academic Admin"]),
			patch("ifitwala_ed.hr.leave_permissions._get_user_org_scope", return_value=["Org A", "Org B"]),
		):
			condition = leave_permissions.get_permission_query_conditions(
				"Leave Application",
				"admin@example.com",
			)

		self.assertIn("`tabLeave Application`.`organization` IN", condition)
		self.assertIn("Org A", condition)
		self.assertIn("Org B", condition)

	def test_leave_encashment_permission_denied_when_feature_disabled(self):
		doc = frappe._dict(employee="HR-EMP-0001")
		with patch("frappe.db.get_single_value", return_value=0):
			allowed = leave_permissions.leave_encashment_has_permission(
				doc,
				user="hr@example.com",
				ptype="read",
			)

		self.assertFalse(allowed)

	def test_leave_encashment_query_condition_is_empty_when_feature_disabled(self):
		with patch("frappe.db.get_single_value", return_value=0):
			condition = leave_permissions.leave_encashment_pqc(user="hr@example.com")

		self.assertEqual(condition, "1=0")

	def test_leave_control_panel_permission_allows_hr_roles(self):
		with patch("frappe.get_roles", return_value=["HR User"]):
			allowed = leave_permissions.leave_control_panel_has_permission(
				frappe._dict(),
				user="hr@example.com",
				ptype="read",
			)

		self.assertTrue(allowed)
