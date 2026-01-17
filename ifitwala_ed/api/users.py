# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/users.py

import frappe

def redirect_user_to_entry_portal():
	"""
	Authoritative login routing.

	Employees NEVER land in Desk.
	Students NEVER land in Desk.

	Desk remains for System Manager / Admin only.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		return

	roles = set(frappe.get_roles(user))

	# Active employee → staff portal
	if (
		"Employee" in roles
		and frappe.db.exists("Employee", {"user_id": user, "status": "Active"})
	):
		frappe.db.set_value("User", user, "home_page", "/portal/staff")
		frappe.local.response["redirect_to"] = "/portal/staff"
		return

	# Student → student portal
	if "Student" in roles and frappe.db.exists("Student", {"student_user_id": user}):
		frappe.db.set_value("User", user, "home_page", "/sp")
		frappe.local.response["redirect_to"] = "/sp"
		return


@frappe.whitelist()
def get_users_with_role(doctype, txt, searchfield, start, page_len, filters):
	"""Return enabled users matching the provided role for link-field queries."""
	role = filters.get("role") if filters else None
	if not role:
		return []

	query = """
		SELECT u.name, u.full_name
		FROM `tabUser` u
		JOIN `tabHas Role` r ON u.name = r.parent
		WHERE r.role = %(role)s
			AND u.enabled = 1
			AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY u.name
		LIMIT %(start)s, %(page_len)s
	"""

	return frappe.db.sql(
		query,
		{
			"role": role,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)
