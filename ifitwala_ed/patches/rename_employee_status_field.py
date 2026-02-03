# ifitwala_ed/patches/rename_employee_status_field.py

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("hr", "doctype", "employee")
	if frappe.db.has_column("Employee", "status") and not frappe.db.has_column("Employee", "employment_status"):
		rename_field("Employee", "status", "employment_status")
		return

	if frappe.db.has_column("Employee", "status") and frappe.db.has_column("Employee", "employment_status"):
		frappe.db.sql(
			"""
			UPDATE `tabEmployee`
			SET employment_status = status
			WHERE (employment_status IS NULL OR employment_status = '')
				AND status IS NOT NULL
			"""
		)
