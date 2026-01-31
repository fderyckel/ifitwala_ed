# ifitwala_ed/patches/set_end_of_year_checklist_defaults.py

import frappe


def execute():
	if not frappe.db.exists("DocType", "End of Year Checklist"):
		return

	status = frappe.db.get_single_value("End of Year Checklist", "status")
	if not status:
		frappe.db.set_single_value("End of Year Checklist", "status", "Draft")
