# ifitwala_ed/hr/leave_permissions.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org

HR_SCOPE_ROLES = {"HR Manager", "HR User", "Academic Admin", "System Manager"}
HR_OVERRIDE_ROLES = {"HR Manager", "HR User", "Academic Admin", "System Manager"}


LEAVE_DOCTYPES_WITH_EMPLOYEE = {
	"Leave Application",
	"Leave Allocation",
	"Leave Policy Assignment",
	"Leave Ledger Entry",
	"Compensatory Leave Request",
	"Leave Adjustment",
	"Leave Encashment",
}


def _get_employee_for_user(user: str) -> str | None:
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "employment_status": ["in", ["Active", "Temporary Leave"]]},
		"name",
	)


def _is_system_or_hr(user: str) -> bool:
	roles = set(frappe.get_roles(user))
	return bool(roles & HR_SCOPE_ROLES)


def _get_user_org_scope(user: str) -> list[str]:
	base_org = get_user_base_org(user)
	if not base_org:
		return []
	return get_descendant_organizations(base_org) or []


def _condition_for_org_scope(doctype: str, org_field: str, user: str) -> str:
	orgs = _get_user_org_scope(user)
	if not orgs:
		return "1=0"
	vals = ", ".join(frappe.db.escape(org) for org in orgs)
	return f"`tab{doctype}`.`{org_field}` IN ({vals})"


def _condition_for_employee_scope(doctype: str, employee_field: str, user: str) -> str:
	employee = _get_employee_for_user(user)
	if not employee:
		return "1=0"
	return f"`tab{doctype}`.`{employee_field}` = {frappe.db.escape(employee)}"


def get_permission_query_conditions(doctype: str, user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None

	if "System Manager" in frappe.get_roles(user):
		return None

	if _is_system_or_hr(user):
		org_field = "organization"
		if doctype == "Leave Policy":
			org_field = "organization"
		return _condition_for_org_scope(doctype, org_field, user)

	if doctype in LEAVE_DOCTYPES_WITH_EMPLOYEE:
		return _condition_for_employee_scope(doctype, "employee", user)

	return "1=0"


def has_permission_for_doc(doc, user: str | None = None, ptype: str | None = None):
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False

	if "System Manager" in frappe.get_roles(user):
		return True

	if _is_system_or_hr(user):
		orgs = set(_get_user_org_scope(user))
		doc_org = doc.get("organization")
		if doc_org:
			return doc_org in orgs
		# fallback for doctypes without explicit organization
		employee = doc.get("employee")
		if employee:
			emp_org = frappe.db.get_value("Employee", employee, "organization")
			return bool(emp_org and emp_org in orgs)
		return False

	employee = _get_employee_for_user(user)
	if not employee:
		return False

	if doc.get("employee"):
		return doc.get("employee") == employee

	return False


def leave_application_pqc(user=None):
	return get_permission_query_conditions("Leave Application", user)


def leave_application_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def leave_allocation_pqc(user=None):
	return get_permission_query_conditions("Leave Allocation", user)


def leave_allocation_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def leave_policy_assignment_pqc(user=None):
	return get_permission_query_conditions("Leave Policy Assignment", user)


def leave_policy_assignment_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def leave_ledger_entry_pqc(user=None):
	return get_permission_query_conditions("Leave Ledger Entry", user)


def leave_ledger_entry_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def leave_period_pqc(user=None):
	return get_permission_query_conditions("Leave Period", user)


def leave_period_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def leave_block_list_pqc(user=None):
	return get_permission_query_conditions("Leave Block List", user)


def leave_block_list_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def compensatory_leave_request_pqc(user=None):
	return get_permission_query_conditions("Compensatory Leave Request", user)


def compensatory_leave_request_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def leave_adjustment_pqc(user=None):
	return get_permission_query_conditions("Leave Adjustment", user)


def leave_adjustment_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def leave_encashment_pqc(user=None):
	if not frappe.db.get_single_value("HR Settings", "enable_leave_encashment"):
		return "1=0"
	return get_permission_query_conditions("Leave Encashment", user)


def leave_encashment_has_permission(doc, user=None, ptype=None):
	if not frappe.db.get_single_value("HR Settings", "enable_leave_encashment"):
		return False
	return has_permission_for_doc(doc, user, ptype)


def leave_policy_pqc(user=None):
	return get_permission_query_conditions("Leave Policy", user)


def leave_policy_has_permission(doc, user=None, ptype=None):
	return has_permission_for_doc(doc, user, ptype)


def leave_control_panel_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	return bool(roles & {"System Manager", "HR Manager", "HR User"})
