# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.hr.expense_claims import (
    EXPENSE_APPROVAL_OVERRIDE_ROLES,
    EXPENSE_FINANCE_ROLES,
)
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org, get_user_base_school
from ifitwala_ed.utilities.school_tree import get_descendant_schools

EXPENSE_CLAIM_SCOPE_ROLES = EXPENSE_APPROVAL_OVERRIDE_ROLES | EXPENSE_FINANCE_ROLES


def _get_employee_for_user(user: str) -> str | None:
    return frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": ["in", ["Active", "Temporary Leave"]]},
        "name",
    )


def _get_org_scope(user: str) -> list[str]:
    base_org = get_user_base_org(user)
    if not base_org:
        return []
    return get_descendant_organizations(base_org) or []


def _get_school_scope(user: str) -> list[str]:
    base_school = get_user_base_school(user)
    if not base_school:
        return []
    return get_descendant_schools(base_school) or [base_school]


def _escape_in(values: list[str]) -> str:
    return ", ".join(frappe.db.escape(value) for value in sorted(set(values)))


def _is_administrator(user: str) -> bool:
    return user == "Administrator"


def _is_scoped_admin(user: str) -> bool:
    return bool(set(frappe.get_roles(user)) & EXPENSE_CLAIM_SCOPE_ROLES)


def _org_scope_condition(doctype: str, user: str) -> str:
    orgs = _get_org_scope(user)
    if not orgs:
        return "1=0"
    return f"`tab{doctype}`.`organization` IN ({_escape_in(orgs)})"


def _school_scope_condition(doctype: str, user: str) -> str:
    schools = _get_school_scope(user)
    if not schools:
        return "1=1"
    field = f"`tab{doctype}`.`school`"
    return f"({field} IN ({_escape_in(schools)}) OR COALESCE({field}, '') = '')"


def _employee_or_approver_condition(doctype: str, user: str) -> str:
    employee = _get_employee_for_user(user)
    employee_condition = "1=0"
    if employee:
        employee_condition = f"`tab{doctype}`.`employee` = {frappe.db.escape(employee)}"
    approver_condition = f"`tab{doctype}`.`expense_approver` = {frappe.db.escape(user)}"
    return f"(({employee_condition}) OR ({approver_condition}))"


def expense_claim_pqc(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "1=0"
    if _is_administrator(user):
        return None

    if _is_scoped_admin(user):
        return " AND ".join(
            condition
            for condition in [
                _org_scope_condition("Expense Claim", user),
                _school_scope_condition("Expense Claim", user),
            ]
            if condition
        )

    return _employee_or_approver_condition("Expense Claim", user)


def expense_claim_has_permission(doc, user=None, ptype=None):
    del ptype

    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    if _is_administrator(user):
        return True

    if doc.get("expense_approver") == user:
        return True

    employee = _get_employee_for_user(user)
    if employee and doc.get("employee") == employee:
        return True

    if not _is_scoped_admin(user):
        return False

    orgs = set(_get_org_scope(user))
    if not orgs or doc.get("organization") not in orgs:
        return False

    schools = set(_get_school_scope(user))
    doc_school = (doc.get("school") or "").strip()
    if schools and doc_school and doc_school not in schools:
        return False

    return True
