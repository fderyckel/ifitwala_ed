# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe

def get_all_employee_emails(organization):
    """
    Returns a list of employee emails, prioritizing company_email, then user_id, then personal_email.

    Args:
        company (str): The name of the company.

    Returns:
        list: A list of email addresses.
    """
    employee_emails = []

    try:
        employee_data = frappe.db.get_values(
            "Employee",
            filters={"status": "Active", "organization": organization},
            fields=["user_id", "employee_professional_email", "employee_personal_email"],
            as_dict=True,  # Important for easier access to fields
        )

        for employee in employee_data:
            email = employee.employee_professional_email or employee.user_id or employee.employee_personal_email
            if email:
                employee_emails.append(email)

    except Exception as e:
        frappe.log_error(f"Error getting employee emails for company {organization}: {e}")

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