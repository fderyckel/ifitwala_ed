from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Employee") or not frappe.db.table_exists("User"):
        return

    has_contact_table = frappe.db.table_exists("Contact")

    employee_rows = frappe.get_all(
        "Employee",
        filters={"employment_status": "Active"},
        fields=["name", "user_id", "employee_professional_email"],
        limit=100000,
    )

    for employee_row in employee_rows:
        _backfill_employee_user_link(employee_row=employee_row, has_contact_table=has_contact_table)


def _backfill_employee_user_link(*, employee_row: dict, has_contact_table: bool) -> None:
    employee_name = str(employee_row.get("name") or "").strip()
    current_user_id = str(employee_row.get("user_id") or "").strip()
    professional_email = str(employee_row.get("employee_professional_email") or "").strip()
    if not employee_name or current_user_id or not professional_email:
        return

    matching_users = frappe.get_all(
        "User",
        filters={"email": professional_email},
        fields=["name"],
        limit=2,
    )
    if len(matching_users) != 1:
        return

    user_name = str(matching_users[0].get("name") or "").strip()
    if not user_name:
        return

    linked_employee_name = frappe.db.get_value("Employee", {"user_id": user_name}, "name")
    if linked_employee_name and linked_employee_name != employee_name:
        return

    frappe.db.set_value("Employee", employee_name, "user_id", user_name, update_modified=False)

    employee_doc = frappe.get_doc("Employee", employee_name)
    employee_doc.user_id = user_name

    from ifitwala_ed.hr.employee_access import sync_user_access_from_employee

    sync_user_access_from_employee(employee_doc)

    if not has_contact_table:
        return

    contact_name = employee_doc._get_or_create_primary_contact()
    if not contact_name:
        return

    employee_doc._ensure_contact_employee_link(contact_name)
    if employee_doc.empl_primary_contact != contact_name:
        employee_doc.empl_primary_contact = contact_name
        employee_doc.db_set("empl_primary_contact", contact_name, update_modified=False)
