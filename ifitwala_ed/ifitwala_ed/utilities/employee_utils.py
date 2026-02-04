# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/employee_utils.py

import frappe
from frappe.utils.nestedset import get_ancestors_of, get_descendants_of

CACHE_TTL = 300  # seconds

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


# -------------------------
# Organization tree helpers
# -------------------------

def _org_cache_key(kind: str, org: str) -> str:
	return f"org:{kind}:{org}"


def get_descendant_organizations(org: str) -> list[str]:
	if not org:
		return []
	cache = frappe.cache()
	key = _org_cache_key("desc", org)
	cached = cache.get_value(key)
	if cached is not None:
		return cached

	# self + descendants using lft/rgt
	org_doc = frappe.get_doc("Organization", org)
	rows = frappe.get_all(
		"Organization",
		filters={"lft": (">=", org_doc.lft), "rgt": ("<=", org_doc.rgt)},
		pluck="name",
	)
	cache.set_value(key, rows, expires_in_sec=CACHE_TTL)
	return rows


def get_ancestor_organizations(org: str) -> list[str]:
	if not org:
		return []
	cache = frappe.cache()
	key = _org_cache_key("anc", org)
	cached = cache.get_value(key)
	if cached is not None:
		return cached

	org_doc = frappe.get_doc("Organization", org)
	rows = frappe.get_all(
		"Organization",
		filters={"lft": ("<=", org_doc.lft), "rgt": (">=", org_doc.rgt)},
		pluck="name",
	)
	cache.set_value(key, rows, expires_in_sec=CACHE_TTL)
	return rows


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
		holiday_list, organization = frappe.db.get_value("Employee", employee, ["current_holiday_list", "organization"])
	else:
		holiday_list = ""
		organization = frappe.db.get_value("Global Defaults", "None", "default_organization")
