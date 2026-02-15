# ifitwala_ed/hr/leave_api.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


class PWANotificationsMixin:
	"""Compatibility shim for upstream HRMS mixin used by Leave Application."""

	def notify_approver(self):
		return None

	def notify_approval_status(self):
		return None


@frappe.whitelist()
def get_current_employee_info():
	row = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "employment_status": ["in", ["Active", "Temporary Leave"]]},
		["name", "employee_full_name", "organization", "school", "leave_approver"],
		as_dict=True,
	)
	return row or {}


def get_employee_email(employee: str) -> str | None:
	if not employee:
		return None

	row = frappe.db.get_value(
		"Employee",
		employee,
		["employee_professional_email", "user_id", "employee_personal_email"],
		as_dict=True,
	)
	if not row:
		return None

	return row.employee_professional_email or row.user_id or row.employee_personal_email


def refetch_resource(*_args, **_kwargs):
	"""No-op shim. Portal resource cache invalidation is out of scope for this phase."""
	return None
