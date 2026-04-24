# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/utilities/employee_utils.py

from __future__ import annotations

import frappe

from ifitwala_ed.utilities.tree_utils import get_ancestors_inclusive, get_descendants_inclusive

CACHE_TTL = 300  # seconds


def _clean_scope_value(value) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _get_user_default_scope_value(user: str, key: str) -> str | None:
    defaults = getattr(frappe, "defaults", None)
    if not defaults or not hasattr(defaults, "get_user_default"):
        return None

    try:
        value = defaults.get_user_default(key, user=user)
    except TypeError:
        value = defaults.get_user_default(key, user)

    return _clean_scope_value(value)


def _get_active_employee_scope(user: str) -> dict[str, str | bool | None]:
    row = (
        frappe.db.get_value(
            "Employee",
            {"user_id": user, "employment_status": "Active"},
            ["name", "organization", "school"],
            as_dict=True,
        )
        or {}
    )
    return {
        "has_active_employee": bool(_clean_scope_value(row.get("name"))),
        "organization": _clean_scope_value(row.get("organization")),
        "school": _clean_scope_value(row.get("school")),
    }


# -------------------------
# Base org / school for user
# -------------------------


def get_user_base_org(user: str | None = None) -> str | None:
    user = user or frappe.session.user
    row = frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": "Active"},
        ["organization"],
        as_dict=True,
    )
    return row.organization if row and row.organization else None


def get_user_base_school(user: str | None = None) -> str | None:
    user = user or frappe.session.user
    row = frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": "Active"},
        ["school"],
        as_dict=True,
    )
    return row.school if row and row.school else None


def get_user_visible_schools(user: str | None = None) -> list[str]:
    """
    Return the Desk school visibility scope for the current staff context.

    Precedence:
    1. Active Employee.school -> that school plus descendants.
    2. No active Employee profile -> persisted default school plus descendants.
    3. No school scope -> active Employee.organization (or persisted default
       organization) -> descendant organizations -> every school in that org scope.

    When an active Employee exists with a blank school, do not revive a stale
    default school; fall back to organization scope instead.
    """
    user = user or frappe.session.user
    scope = _get_active_employee_scope(user)

    school = scope["school"]
    if not school and not scope["has_active_employee"]:
        school = _get_user_default_scope_value(user, "school")

    if school:
        descendants = get_descendants_inclusive("School", school, cache_ttl=CACHE_TTL) or [school]
        return list(dict.fromkeys(_clean_scope_value(item) for item in descendants if _clean_scope_value(item)))

    organization = scope["organization"] or _get_user_default_scope_value(user, "organization")
    if not organization:
        return []

    organizations = get_descendant_organizations(organization) or [organization]
    organizations = list(dict.fromkeys(_clean_scope_value(item) for item in organizations if _clean_scope_value(item)))
    if not organizations:
        return []

    schools = frappe.get_all(
        "School",
        filters={"organization": ["in", organizations]},
        pluck="name",
        order_by="lft asc, name asc",
        limit=0,
    )
    return list(dict.fromkeys(_clean_scope_value(item) for item in (schools or []) if _clean_scope_value(item)))


def get_descendant_organizations(org: str) -> list[str]:
    return get_descendants_inclusive("Organization", org, cache_ttl=CACHE_TTL)


def get_ancestor_organizations(org: str) -> list[str]:
    return get_ancestors_inclusive("Organization", org, cache_ttl=CACHE_TTL)


def is_leaf_organization(org: str) -> bool:
    # leaf when only self in descendants list
    desc = get_descendant_organizations(org)
    return len(desc) == 1


def get_all_employee_emails(organization):
    """
    Returns a list of employee emails, prioritizing organization_email, then user_id, then personal_email.

    Args:
        organization (str): The name of the organization.

    Returns:
        list: A list of email addresses.
    """
    employee_emails = []

    try:
        employee_data = frappe.db.get_values(
            "Employee",
            filters={"employment_status": "Active", "organization": organization},
            fields=["user_id", "employee_professional_email", "employee_personal_email"],
            as_dict=True,  # Important for easier access to fields
        )

        for employee in employee_data:
            email = employee.employee_professional_email or employee.user_id or employee.employee_personal_email
            if email:
                employee_emails.append(email)

    except Exception as e:
        frappe.log_error(f"Error getting employee emails for organization {organization}: {e}")

    return employee_emails


def get_employee_emails(employee_list):
    """
    Returns a list of employee emails, prioritizing user_id, then employee_professional_email, then employee_personal_email.

    Args:
        employee_list (list): A list of employee names or IDs.

    Returns:
        list: A list of email addresses.
    """
    employee_emails = []

    if not employee_list:
        return []  # Return empty list if employee_list is empty

    try:
        employee_data = frappe.db.get_values(
            "Employee",
            filters={"name": ("in", employee_list)},
            fields=["user_id", "employee_professional_email", "employee_personal_email"],
            as_dict=True,
        )

        for employee in employee_data:
            email = employee.employee_professional_email or employee.user_id or employee.employee_personal_email
            if email:
                employee_emails.append(email)

    except Exception as e:
        frappe.log_error(f"Error getting employee emails for employees {employee_list}: {e}")

    return employee_emails


def get_holiday_list_for_employee(employee, raise_exception=True):
    if employee:
        _holiday_list, _organization = frappe.db.get_value(
            "Employee", employee, ["current_holiday_list", "organization"]
        )
    else:
        _holiday_list = ""
        _organization = frappe.db.get_value("Global Defaults", "None", "default_organization")
