# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org, get_user_base_school
from ifitwala_ed.utilities.school_tree import get_descendant_schools

PD_SCOPE_ROLES = {"HR Manager", "HR User", "Academic Admin", "System Manager"}
PD_FINANCE_ROLES = {"Accounts Manager", "Accounts User"}
PD_ALL_SCOPED_ROLES = PD_SCOPE_ROLES | PD_FINANCE_ROLES
PD_EMPLOYEE_SELF_DOCTYPES = {
    "Professional Development Request",
    "Professional Development Record",
    "Professional Development Outcome",
}
PD_SCHOOL_SCOPED_DOCTYPES = {
    "Professional Development Theme",
    "Professional Development Budget",
    "Professional Development Request",
    "Professional Development Record",
    "Professional Development Outcome",
    "Professional Development Encumbrance",
}


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


def _is_system_manager(user: str) -> bool:
    return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def _is_scoped_admin(user: str) -> bool:
    return bool(set(frappe.get_roles(user)) & PD_ALL_SCOPED_ROLES)


def _escape_in(values: list[str]) -> str:
    return ", ".join(frappe.db.escape(value) for value in sorted(set(values)))


def _school_scope_condition(doctype: str, user: str) -> str:
    schools = _get_school_scope(user)
    if not schools:
        return "1=0"
    field = f"`tab{doctype}`.`school`"
    escaped = _escape_in(schools)
    return f"({field} IN ({escaped}) OR COALESCE({field}, '') = '')"


def _org_scope_condition(doctype: str, user: str) -> str:
    orgs = _get_org_scope(user)
    if not orgs:
        return "1=0"
    escaped = _escape_in(orgs)
    return f"`tab{doctype}`.`organization` IN ({escaped})"


def _employee_scope_condition(doctype: str, user: str) -> str:
    employee = _get_employee_for_user(user)
    if not employee:
        return "1=0"
    return f"`tab{doctype}`.`employee` = {frappe.db.escape(employee)}"


def get_permission_query_conditions(doctype: str, user: str | None = None) -> str | None:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "1=0"

    if _is_system_manager(user):
        return None

    if _is_scoped_admin(user):
        conditions = [_org_scope_condition(doctype, user)]
        if doctype in PD_SCHOOL_SCOPED_DOCTYPES:
            conditions.append(_school_scope_condition(doctype, user))
        return " AND ".join(f"({condition})" for condition in conditions if condition)

    if doctype in PD_EMPLOYEE_SELF_DOCTYPES:
        return _employee_scope_condition(doctype, user)

    return "1=0"


def has_permission_for_doc(doc, user: str | None = None, ptype: str | None = None):
    del ptype

    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    if _is_system_manager(user):
        return True

    if _is_scoped_admin(user):
        orgs = set(_get_org_scope(user))
        if not orgs:
            return False

        doc_org = (doc.get("organization") or "").strip()
        if doc_org and doc_org not in orgs:
            return False

        if doc.doctype in PD_SCHOOL_SCOPED_DOCTYPES:
            schools = set(_get_school_scope(user))
            doc_school = (doc.get("school") or "").strip()
            if doc_school and doc_school not in schools:
                return False

        return True

    if doc.doctype in PD_EMPLOYEE_SELF_DOCTYPES:
        employee = _get_employee_for_user(user)
        return bool(employee and doc.get("employee") == employee)

    return False


def professional_development_theme_pqc(user=None):
    return get_permission_query_conditions("Professional Development Theme", user)


def professional_development_theme_has_permission(doc, user=None, ptype=None):
    return has_permission_for_doc(doc, user, ptype)


def professional_development_budget_pqc(user=None):
    return get_permission_query_conditions("Professional Development Budget", user)


def professional_development_budget_has_permission(doc, user=None, ptype=None):
    return has_permission_for_doc(doc, user, ptype)


def professional_development_request_pqc(user=None):
    return get_permission_query_conditions("Professional Development Request", user)


def professional_development_request_has_permission(doc, user=None, ptype=None):
    return has_permission_for_doc(doc, user, ptype)


def professional_development_record_pqc(user=None):
    return get_permission_query_conditions("Professional Development Record", user)


def professional_development_record_has_permission(doc, user=None, ptype=None):
    return has_permission_for_doc(doc, user, ptype)


def professional_development_outcome_pqc(user=None):
    return get_permission_query_conditions("Professional Development Outcome", user)


def professional_development_outcome_has_permission(doc, user=None, ptype=None):
    return has_permission_for_doc(doc, user, ptype)


def professional_development_encumbrance_pqc(user=None):
    return get_permission_query_conditions("Professional Development Encumbrance", user)


def professional_development_encumbrance_has_permission(doc, user=None, ptype=None):
    return has_permission_for_doc(doc, user, ptype)
